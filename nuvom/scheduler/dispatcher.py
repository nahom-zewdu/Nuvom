# nuvom/scheduler/dispatcher.py

"""
Scheduler Dispatcher
====================

Turns due *scheduled* envelopes into regular execution `Job`s and pushes them
onto the main queue. The dispatcher is intentionally stateless and can be
scaled horizontally (multiple processes may run concurrently), while the
backend provides the necessary consistency.

Responsibilities
----------------
- Poll the scheduler backend for *due* `ScheduleEnvelope`s.
- Convert each envelope into a `Job` (mirroring Task defaults when possible).
- Enqueue the `Job` into the main queue with the envelope's priority.
- Acknowledge handoff and handle recurrence:
    * one_off   → ack → cancel
    * interval  → ack → compute next run → reschedule(pending)
    * cron      → ack → compute next run via cron logic → reschedule(pending)

Concurrency & Idempotency
-------------------------
The dispatcher **does not** perform exclusive claiming. Backends should:
- Return only `pending` items from `due()`.
- Make `ack_dispatched()`, `reschedule()`, `cancel()` resilient (idempotent).
This keeps the dispatcher simple and allows multiple dispatchers to run.

Cron Support
------------
Cron next-occurrence computation uses `croniter` if installed. If missing,
cron scheduling will raise a `RuntimeError` when encountered. This avoids
adding a hard dependency at the framework level while keeping behavior explicit.

Public API
----------
- `dispatch_once(now_ts: float | None = None, limit: int | None = None) -> int`
- `Dispatcher` class:
    - `run_once(...)`
    - `run_forever(poll_interval=1.0, batch_size=100, jitter=0.0, stop_event=None)`

Design Notes
------------
- We attempt to copy Task-defined execution defaults (timeout, retries, hooks)
  at dispatch time so that scheduled jobs behave like `.delay()` jobs.
- On success, we always `ack_dispatched()` before any further lifecycle change.
  For recurring schedules, we then `reschedule(...)` to transition back to
  `pending` with a strictly future `next_run_ts`.
"""

from __future__ import annotations

import math
import time
from typing import Optional

from nuvom.log import get_logger
from nuvom.job import Job
from nuvom.queue import enqueue
from nuvom.task import get_task
from nuvom.scheduler.backend import get_scheduler_backend
from nuvom.scheduler.models import ScheduleEnvelope

logger = get_logger()

# ------------------------------ cron helpers ------------------------------ #

def _compute_next_cron_ts(cron_expr: str, tz_name: str, after_ts: float) -> float:
    """
    Compute the next cron fire time (UNIX timestamp, UTC seconds) strictly after `after_ts`.

    This uses `croniter` if available. We interpret the envelope's `timezone`
    using Python's `zoneinfo` (Py>=3.9). The returned value is UTC epoch seconds.

    Raises
    ------
    RuntimeError
        If `croniter` is not available.
    """
    try:
        from croniter import croniter  # type: ignore
    except Exception as e:  # pragma: no cover - optional dependency path
        raise RuntimeError(
            "Cron schedules require the 'croniter' package. "
            "Install it or choose a non-cron schedule."
        ) from e

    try:
        # Resolve timezone
        try:
            from zoneinfo import ZoneInfo  # Python 3.9+
            tz = ZoneInfo(tz_name or "UTC")
        except Exception:
            # Fallback: treat as UTC if tz database not available
            from datetime import timezone as _tz
            tz = _tz.utc

        # Build timezone-aware 'after' datetime
        from datetime import datetime, timezone
        after_dt_utc = datetime.fromtimestamp(after_ts, tz=timezone.utc)
        # Convert to target TZ for cron evaluation
        after_dt_local = after_dt_utc.astimezone(tz)

        # Compute next local occurrence strictly after 'after_dt_local'
        itr = croniter(cron_expr, after_dt_local)
        next_local = itr.get_next(datetime, is_dst=None)  # type: ignore

        # Convert back to UTC seconds
        next_utc = next_local.astimezone(timezone.utc)
        return float(next_utc.timestamp())
    except Exception as e:
        logger.exception("[dispatcher] Failed computing cron next fire time.")
        raise


# ----------------------------- job conversion ----------------------------- #

def _to_job(envelope: ScheduleEnvelope) -> Job:
    """
    Convert a `ScheduleEnvelope` into a fully-configured `Job`.

    We consult the Task registry to mirror the same execution parameters
    a `.delay()` submission would use (timeouts, retries, hooks, etc).
    If the Task is missing (shouldn't happen in healthy systems), we still
    build a minimal `Job` so the failure is visible in worker logs.
    """
    t = get_task(envelope.task_name)

    # Mirror Task.delay() parameters if task exists
    if t is not None:
        return Job(
            func_name=envelope.task_name,
            args=tuple(envelope.args),
            kwargs=dict(envelope.kwargs),
            retries=t.retries,
            store_result=t.store_result,
            timeout_secs=t.timeout_secs,
            retry_delay_secs=t.retry_delay_secs,
            timeout_policy=t.timeout_policy,
            before_job=t.before_job,
            after_job=t.after_job,
            on_error=t.on_error,
            priority=envelope.priority,
            scheduled=True,
        )

    # Fallback minimal job
    logger.warning(
        "[dispatcher] Task '%s' not found in registry; dispatching minimal job.",
        envelope.task_name,
    )
    return Job(
        func_name=envelope.task_name,
        args=tuple(envelope.args),
        kwargs=dict(envelope.kwargs),
        priority=envelope.priority,
        scheduled=True,
    )


# ---------------------------- recurrence logic ---------------------------- #

def _next_run_after(envelope: ScheduleEnvelope, after_ts: float) -> Optional[float]:
    """
    Compute the next run timestamp (UTC seconds) strictly after `after_ts`.

    - one_off: None (no subsequent run)
    - interval: add N * interval_secs so that result > after_ts
    - cron: compute via croniter (optional dependency)

    Returns
    -------
    Optional[float]
        Next run ts or None for one_off.
    """
    if envelope.schedule_type == "one_off":
        return None

    if envelope.schedule_type == "interval":
        if not envelope.interval_secs or envelope.interval_secs <= 0:
            raise ValueError("interval_secs must be > 0 for interval schedules.")
        base = envelope.next_run_ts if envelope.next_run_ts is not None else after_ts
        # ensure strictly future
        n = max(1, int(math.floor((after_ts - base) / envelope.interval_secs)) + 1)
        return float(base + n * envelope.interval_secs)

    if envelope.schedule_type == "cron":
        if not envelope.cron_expr:
            raise ValueError("cron_expr required for cron schedules.")
        return _compute_next_cron_ts(envelope.cron_expr, envelope.timezone, after_ts)

    raise ValueError(f"Unsupported schedule_type: {envelope.schedule_type}")


# ------------------------------ dispatch core ----------------------------- #

def dispatch_once(now_ts: Optional[float] = None, limit: Optional[int] = 100, backend = None) -> int:
    """
    Poll the backend for due envelopes and dispatch them once.

    Parameters
    ----------
    now_ts : float, optional
        Evaluation time in UNIX seconds. Defaults to current time.
    limit : int, optional
        Maximum number of envelopes to dispatch in this call.

    Returns
    -------
    int
        Number of envelopes successfully enqueued to the main queue.
    """
    if backend is None:
        backend = get_scheduler_backend()
    
    now = now_ts if now_ts is not None else time.time()

    try:
        due = backend.due(now_ts=now, limit=limit)
    except Exception:
        logger.exception("[dispatcher] Failed to query due schedules.")
        return 0

    dispatched = 0
    for env in due:
        try:
            job = _to_job(env)
            enqueue(job)

            # Ack *successful* handoff
            backend.ack_dispatched(env.id)

            # Recurrence handling
            if env.schedule_type == "one_off":
                # No more runs → cancel to keep storage tidy
                backend.cancel(env.id)
            else:
                next_ts = _next_run_after(env, after_ts=now)
                if next_ts is None:
                    # Defensive: treat as one_off
                    backend.cancel(env.id)
                else:
                    backend.reschedule(env.id, next_ts)

            dispatched += 1
        except Exception as e:
            # We purposely do not ack/cancel on failure to enqueue.
            logger.exception(
                "[dispatcher] Failed dispatching schedule id=%s task=%s: %s",
                getattr(env, "id", "?"),
                getattr(env, "task_name", "?"),
                e,
            )
            # Continue other envelopes

    if dispatched:
        logger.debug("[dispatcher] Dispatched %d envelope(s).", dispatched)
    return dispatched


# ------------------------------ loop runner -------------------------------- #

class Dispatcher:
    """
    Simple loop runner for the scheduler dispatcher.

    This class contains *no* business logic beyond calling `dispatch_once`;
    it only manages a polling loop with optional jitter and cooperative stop.

    Example
    -------
        from threading import Event
        stop = Event()
        d = Dispatcher()
        d.run_forever(poll_interval=1.0, batch_size=100, jitter=0.2, stop_event=stop)
    """

    def run_once(self, batch_size: int = 100) -> int:
        """
        Dispatch up to `batch_size` due envelopes immediately.

        Returns the number of envelopes dispatched.
        """
        return dispatch_once(limit=batch_size)

    def run_forever(
        self,
        *,
        poll_interval: float = 1.0,
        batch_size: int = 100,
        jitter: float = 0.0,
        stop_event=None,
    ) -> None:
        """
        Run a cooperative polling loop.

        Parameters
        ----------
        poll_interval : float
            Base sleep seconds between polls when nothing is due.
        batch_size : int
            Maximum number of envelopes dispatched per iteration.
        jitter : float
            Random additive jitter in seconds to reduce sync across replicas.
        stop_event : threading.Event | None
            Optional external event to request shutdown.
        """
        import random

        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if jitter < 0:
            raise ValueError("jitter must be non-negative")

        logger.info(
            "[dispatcher] Loop starting (poll=%.3fs, batch=%d, jitter=%.3fs)",
            poll_interval,
            batch_size,
            jitter,
        )

        try:
            while True:
                count = 0
                try:
                    count = dispatch_once(limit=batch_size)
                except Exception:
                    # Defensive: never crash the loop; log and continue.
                    logger.exception("[dispatcher] dispatch_once raised unexpectedly.")

                # If we dispatched something, loop again immediately to drain.
                if count == 0:
                    sleep_for = poll_interval + (random.random() * jitter if jitter else 0.0)
                    if stop_event is not None and getattr(stop_event, "wait", None):
                        # Cooperative sleep with early wake-up
                        if stop_event.wait(timeout=sleep_for):
                            break
                    else:
                        time.sleep(sleep_for)

                if stop_event is not None and getattr(stop_event, "is_set", None) and stop_event.is_set():
                    break
        finally:
            logger.info("[dispatcher] Loop exiting")
