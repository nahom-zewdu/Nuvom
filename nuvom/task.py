"""
Task abstraction and scheduling entrypoint for Nuvom
===================================================

This module defines the core `Task` wrapper used by Nuvom to integrate ordinary
Python callables with the platform's **execution** and **scheduling** systems.
It exposes a unified API for:

- **Immediate execution** via :py:meth:`Task.delay` and :py:meth:`Task.map`.
- **Deferred/recurring execution** via :py:meth:`Task.schedule` which pushes a
  *schedule envelope* into the **scheduler queue** (separate from the main job
  queue). A background scheduler component later dequeues due items and
  transforms them into high-priority jobs on the main queue.

The design follows these principles:

1. **Separation of concerns** — Tasks do not compute their next run time beyond
   simple cases; instead they emit a schedule envelope that the scheduler
   backend is responsible for interpreting and dispatching.
2. **Non-invasive** — Existing `.delay()` and `.map()` semantics are preserved.
3. **Backend-agnostic** — The schedule envelope has a stable schema, but the
   persistence/transport is delegated to `nuvom.scheduler.queue.get_scheduler_backend()`.
4. **UTC-first** — All absolute times are normalized to UTC for correctness.


Required external modules (do not assume implementations)
--------------------------------------------------------
This module **expects** (but does not implement) the following public surface:

- ``nuvom.scheduler.queue.get_scheduler_backend()`` → object with method
  ``enqueue(envelope: dict) -> Any``

You can provide any backend (in-memory, Redis, SQL) as long as it accepts the
schedule envelope described below.


Schedule Envelope (contract)
----------------------------
The dictionary pushed to the scheduler queue has the following fields. Backends
and the scheduler loop should treat this as the canonical schema:

.. code-block:: python

    {
        "id": str,                       # UUID for this scheduled reference
        "task_name": str,               # Registered task name
        "args": list,                   # Task positional args
        "kwargs": dict,                 # Task keyword args
        "created_at_ts": float,         # UNIX seconds (UTC)
        "next_run_ts": float | None,    # First due time (scheduler may recompute)
        "schedule": {
            "type": "once" | "interval" | "cron",
            "at_ts": float | None,         # absolute UTC ts (for once)
            "interval_secs": int | None,   # > 0 (for interval)
            "cron_expr": str | None,       # e.g. "0 0 * * *" (for cron)
            "timezone": str | None,        # IANA TZ (cron evaluation)
        },
        "metadata": {
            "category": str,
            "description": str,
            "tags": list[str],
        },
    }

The **scheduler service** is responsible for:
- Dequeuing items, honoring misfire policy if your design includes one.
- Computing subsequent `next_run_ts` for interval/cron types.
- Emitting a high-priority main-queue job when an item becomes due.

Note: This module **does not** assume or implement misfire policy, locking, or
concurrency limits. Extend the envelope if/when those concerns are added.
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Literal, Optional
from uuid import uuid4

from nuvom.config import get_settings
from nuvom.job import Job
from nuvom.queue import get_queue_backend
from nuvom.registry.registry import get_task_registry

# Deliberate soft dependency: we *use* the accessor but do not dictate its impl.
from nuvom.scheduler.queue import get_scheduler_backend  # type: ignore


# -------------------------------------------------------------------- #
# Helper utilities
# -------------------------------------------------------------------- #
def _coerce_tags(raw: Any | None) -> List[str]:
    """Normalize the ``tags`` parameter into a strict list of strings.

    Parameters
    ----------
    raw : Any | None
        May be a single string, an iterable of strings, or ``None``.

    Returns
    -------
    List[str]
        A list of tag strings.

    Raises
    ------
    TypeError
        If input contains non-string values or is an unsupported type.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, Iterable):
        coerced: list[str] = []
        for t in raw:
            if not isinstance(t, str):
                raise TypeError("All tags must be strings.")
            coerced.append(t)
        return coerced
    raise TypeError("tags must be str, List[str], or None.")


def _default_timeout(provided: int | None) -> int | None:
    """Resolve timeout for jobs.

    Uses the provided timeout value if set; otherwise falls back to the global
    setting ``job_timeout_secs``.

    Parameters
    ----------
    provided : int | None
        Explicit timeout in seconds, or ``None`` to use the global default.

    Returns
    -------
    int | None
        Effective timeout value.
    """
    return provided if provided is not None else get_settings().job_timeout_secs


def _default_retry_delay(provided: int | None) -> int | None:
    """Resolve retry delay for jobs.

    Uses the provided retry delay if set; otherwise falls back to the global
    setting ``retry_delay_secs``.

    Parameters
    ----------
    provided : int | None
        Explicit retry delay in seconds, or ``None`` to use the global default.

    Returns
    -------
    int | None
        Effective retry delay.
    """
    return provided if provided is not None else get_settings().retry_delay_secs


def _utcnow() -> datetime:
    """Return the current UTC time as an aware ``datetime``.

    Notes
    -----
    All absolute times passed into :py:meth:`Task.schedule` are normalized to
    UTC. If a naive ``datetime`` is provided by callers, it is treated as UTC
    with a warning.
    """
    return datetime.now(timezone.utc)


# -------------------------------------------------------------------- #
# Task wrapper
# -------------------------------------------------------------------- #
class Task:
    """Runtime wrapper that integrates a Python function with Nuvom.

    A :class:`Task` provides:

    - **Immediate execution** via :py:meth:`delay` and :py:meth:`map`.
    - **Scheduling** via :py:meth:`schedule`, which emits a schedule envelope to
      a *dedicated scheduler queue* (separate from the main job queue). A
      scheduler service will later create a high-priority job on the main queue
      once the schedule becomes due.
    - **Global discovery/registry** integration for system-wide introspection.

    Parameters
    ----------
    func : Callable
        The function to wrap.
    name : str, optional
        Override the task's registry name. Defaults to ``func.__name__``.
    retries : int
        Number of retries permitted for jobs created by this task.
    store_result : bool
        Whether job results are persisted by the backend.
    timeout_secs : int | None
        Job timeout; falls back to ``get_settings().job_timeout_secs`` if None.
    timeout_policy : {"fail", "retry", "ignore"} | None
        Policy applied when a timeout occurs (backend-specific enforcement).
    retry_delay_secs : int | None
        Per-retry delay; falls back to ``get_settings().retry_delay_secs`` if None.
    tags : list[str] | str | None
        Tags for organization and filtering.
    description : str | None
        Human-friendly description of the task.
    category : str | None
        Logical grouping label. Defaults to ``"default"``.
    before_job, after_job, on_error : Callable | None
        Optional lifecycle hooks invoked by the worker runtime.

    Attributes
    ----------
    name, retries, store_result, timeout_secs, retry_delay_secs, timeout_policy,
    tags, description, category
        See parameter descriptions.
    """

    def __init__(
        self,
        func: Callable,
        *,
        name: Optional[str] = None,
        retries: int = 0,
        store_result: bool = True,
        timeout_secs: Optional[int] = None,
        timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
        retry_delay_secs: int | None = None,
        tags: Optional[list[str] | str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        before_job: Optional[Callable[[], None]] = None,
        after_job: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        functools.update_wrapper(self, func)

        # Core metadata ------------------------------------------------- #
        self.func = func
        self.name = name or func.__name__
        self.retries = retries
        self.store_result = store_result

        self.timeout_secs = _default_timeout(timeout_secs)
        self.retry_delay_secs = _default_retry_delay(retry_delay_secs)
        self.timeout_policy = timeout_policy

        # Optional metadata -------------------------------------------- #
        self.tags = _coerce_tags(tags)
        self.description = description or ""
        self.category = category or "default"

        # Lifecycle hooks ---------------------------------------------- #
        self.before_job = before_job
        self.after_job = after_job
        self.on_error = on_error

        self._register()

    # ---------------------------------------------------------------- #
    # Internal helpers
    # ---------------------------------------------------------------- #
    def _register(self) -> None:
        """Register this task into the global registry.

        Notes
        -----
        - Duplicate registrations are allowed silently (idempotent).
        - A warning is emitted if the task name starts with ``test_`` to help
          avoid clashes with pytest test discovery.
        """
        if self.name.startswith("test_"):
            warnings.warn(
                f"Task '{self.name}' may interfere with pytest collection.",
                stacklevel=3,
            )
        get_task_registry().register(
            self.name,
            self,
            silent=True,
            metadata={
                "tags": self.tags,
                "description": self.description,
                "category": self.category,
            },
        )

    # ---------------------------------------------------------------- #
    # Invocation helpers (immediate execution)
    # ---------------------------------------------------------------- #
    def __call__(self, *args, **kwargs):
        """Execute the wrapped function synchronously and return its result."""
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs) -> Job:
        """Enqueue a job for **immediate execution** on the main queue.

        Parameters
        ----------
        *args, **kwargs
            Arguments forwarded to the wrapped function at execution time.

        Returns
        -------
        Job
            The enqueued job instance (backend-generated fields may be blank
            until persisted by the queue backend).
        """
        job = Job(
            func_name=self.name,
            args=args,
            kwargs=kwargs,
            retries=self.retries,
            store_result=self.store_result,
            timeout_secs=self.timeout_secs,
            retry_delay_secs=self.retry_delay_secs,
            timeout_policy=self.timeout_policy,
            before_job=self.before_job,
            after_job=self.after_job,
            on_error=self.on_error,
        )
        get_queue_backend().enqueue(job)
        return job

    # Alias for API symmetry
    submit = delay

    def map(self, arg_tuples: Iterable[Sequence[Any]]) -> list[Job]:
        """Enqueue multiple jobs for bulk immediate execution.

        Parameters
        ----------
        arg_tuples : Iterable[Sequence[Any]]
            Iterable of positional-argument sequences. Each element becomes a
            separate job: ``task.delay(*args)``.

        Returns
        -------
        list[Job]
            Enqueued jobs, in order.

        Raises
        ------
        TypeError
            If any element of ``arg_tuples`` is not a sequence.
        """
        jobs: list[Job] = []
        for args in arg_tuples:
            if not isinstance(args, Sequence):
                raise TypeError("Each element passed to map() must be a sequence.")
            jobs.append(self.delay(*args))
        return jobs

    # ---------------------------------------------------------------- #
    # Scheduling (deferred/recurring)
    # ---------------------------------------------------------------- #
    def schedule(
        self,
        *args: Any,
        at: datetime | None = None,
        in_: timedelta | None = None,
        interval: int | None = None,
        cron: str | None = None,
        timezone_name: str | None = "UTC",
        **kwargs: Any,
    ) -> dict:
        """Schedule this task for **future or recurring execution**.

        Exactly one of ``at``/``in_``/``interval``/``cron`` must be provided.
        The method constructs a *schedule envelope* and pushes it to the
        scheduler queue via ``get_scheduler_backend().enqueue(envelope)``.

        Parameters
        ----------
        *args : Any
            Positional arguments to apply when the task eventually runs.
        at : datetime, optional
            Absolute due time. If naive, it is interpreted as UTC (a warning is
            emitted) and converted to an aware ``datetime``.
        in_ : timedelta, optional
            Delay from now (UTC). Mutually exclusive with ``at``.
        interval : int, optional
            Fixed interval in seconds for recurring execution. Must be > 0.
        cron : str, optional
            Cron expression (e.g., ``"0 9 * * MON"``). The first run time may
            be computed by the scheduler service. Use ``timezone_name`` for TZ.
        timezone_name : str | None, default "UTC"
            IANA timezone used **by the scheduler** when evaluating cron.
        **kwargs : Any
            Keyword arguments to apply when the task eventually runs.

        Returns
        -------
        dict
            The schedule envelope dictionary that was enqueued. Backends may
            augment it with additional fields (e.g., persistence keys).

        Raises
        ------
        ValueError
            If none or more than one of (``at``, ``in_``, ``interval``,
            ``cron``) is provided, or if ``interval`` is not positive.
        RuntimeError
            If the scheduler backend accessor is missing or invalid.

        Notes
        -----
        - The scheduler service is responsible for turning this envelope into a
          high-priority job on the main queue when it becomes due.
        - The envelope schema is documented at the top of this module.
        """
        # Validate mutually exclusive scheduling modes
        provided = [p is not None for p in (at, in_, interval, cron)]
        if sum(provided) != 1:
            raise ValueError(
                "Specify exactly one of `at`, `in_`, `interval`, or `cron`."
            )

        now = _utcnow()

        # Normalize absolute/relative times and schedule-specific fields
        schedule_type: Literal["once", "interval", "cron"]
        at_ts: float | None = None
        interval_secs: int | None = None
        cron_expr: str | None = None

        if at is not None:
            schedule_type = "once"
            if at.tzinfo is None:
                warnings.warn("Naive datetime passed to schedule(at=...); assuming UTC.")
                at = at.replace(tzinfo=timezone.utc)
            at_ts = at.astimezone(timezone.utc).timestamp()
        elif in_ is not None:
            schedule_type = "once"
            at_ts = (now + in_).timestamp()
        elif interval is not None:
            if interval <= 0:
                raise ValueError("`interval` must be a positive integer (seconds).")
            schedule_type = "interval"
            interval_secs = int(interval)
            # First run happens after one interval by default
            at_ts = (now + timedelta(seconds=interval_secs)).timestamp()
        elif cron is not None:
            schedule_type = "cron"
            cron_expr = cron
            # The scheduler service will compute the next cron fire time.
            at_ts = None
        else:  # pragma: no cover - guarded by mutual exclusivity check above
            raise ValueError("Must specify a valid scheduling mode.")

        envelope: dict[str, Any] = {
            "id": str(uuid4()),
            "task_name": self.name,
            "args": list(args),
            "kwargs": dict(kwargs),
            "created_at_ts": now.timestamp(),
            "next_run_ts": at_ts,
            "schedule": {
                "type": schedule_type,
                "at_ts": at_ts,
                "interval_secs": interval_secs,
                "cron_expr": cron_expr,
                "timezone": timezone_name,
            },
            "metadata": {
                "category": self.category,
                "description": self.description,
                "tags": self.tags,
            },
        }

        # Defer to the scheduler backend (separate queue from the main job queue)
        try:
            scheduler_backend = get_scheduler_backend()  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "Scheduler backend accessor `nuvom.scheduler.queue.get_scheduler_backend()` "
                "is not available or failed. Provide an implementation that returns a backend "
                "with an `enqueue(envelope: dict)` method."
            ) from exc

        if not hasattr(scheduler_backend, "enqueue"):
            raise RuntimeError(
                "Scheduler backend must expose an `enqueue(envelope: dict)` method."
            )

        scheduler_backend.enqueue(envelope)
        return envelope

    # ---------------------------------------------------------------- #
    # Nice repr for debugging
    # ---------------------------------------------------------------- #
    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Task {self.name} "
            f"retries={self.retries} "
            f"timeout={self.timeout_secs}s "
            f"tags={self.tags}>"
        )


# -------------------------------------------------------------------- #
# Decorator factory
# -------------------------------------------------------------------- #

def task(
    _func: Callable | None = None,
    *,
    name: Optional[str] = None,
    retries: int = 0,
    store_result: bool = True,
    timeout_secs: Optional[int] = None,
    timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
    retry_delay_secs: int | None = None,
    tags: list[str] | str | None = None,
    description: str | None = None,
    category: str | None = None,
    before_job: Optional[Callable[[], None]] = None,
    after_job: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
):
    """Decorator that converts a Python function into a Nuvom :class:`Task`.

    Parameters
    ----------
    name : str, optional
        Custom registry name for the task.
    retries : int, default 0
        Number of retry attempts allowed for jobs created by this task.
    store_result : bool, default True
        Whether job results should be persisted.
    timeout_secs : int, optional
        Job timeout in seconds; defaults to the global setting when ``None``.
    timeout_policy : {"fail", "retry", "ignore"} | None
        Policy applied when a timeout occurs.
    retry_delay_secs : int, optional
        Backoff delay between retries; defaults to the global setting when ``None``.
    tags : list[str] | str | None
        Tags for organization and filtering.
    description : str | None
        Human-friendly description for UIs and docs.
    category : str | None
        Logical grouping label. Defaults to ``"default"``.
    before_job, after_job, on_error : Callable | None
        Optional lifecycle hooks used by the worker.

    Returns
    -------
    Task
        A :class:`Task` instance wrapping the provided function.

    Examples
    --------
    >>> @task
    ... def add(x, y):
    ...     return x + y

    >>> @task(retries=2, tags=["math"])  # doctest: +SKIP
    ... def mul(x, y):
    ...     return x * y
    """

    def decorator(func: Callable) -> Task:
        return Task(
            func,
            name=name,
            retries=retries,
            store_result=store_result,
            timeout_secs=timeout_secs,
            timeout_policy=timeout_policy,
            retry_delay_secs=retry_delay_secs,
            tags=tags,
            description=description,
            category=category,
            before_job=before_job,
            after_job=after_job,
            on_error=on_error,
        )

    return decorator if _func is None else decorator(_func)


# -------------------------------------------------------------------- #
# Public helper
# -------------------------------------------------------------------- #

def get_task(name: str) -> Optional[Task]:
    """Return a registered :class:`Task` by name.

    Parameters
    ----------
    name : str
        Task name used during registration.

    Returns
    -------
    Task | None
        The registered task instance or ``None`` if not present.
    """
    return get_task_registry().get(name)
