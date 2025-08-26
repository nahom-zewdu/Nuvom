### nuvom/scheduler/models.py

"""
Scheduler Models
================

Canonical, storage-friendly dataclasses for the scheduler pipeline.

There are two primary structures:

1) ScheduledTaskReference
   -----------------------
   A *user-facing* reference produced by `Task.schedule(...)`. It captures
   the scheduling intent alongside the target task name and payload
   (args/kwargs). It is intentionally permissive and ergonomic for callers.

   The backend converts a reference into a durable `ScheduleEnvelope`.

2) ScheduleEnvelope
   -----------------
   A *backend-facing* record suitable for persistence, de-duplication,
   dispatch bookkeeping, and safe replay across process restarts.

Design goals
------------
- Clear separation of API vs. persistence concerns
- Timezone-safe absolute timestamps (UTC)
- Minimal dependencies (dataclasses; cron parsing handled at dispatch time)
- Extensible metadata surface (free-form dict)

This module contains no I/O; it only validates and transforms data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Literal, Optional
import time
import uuid


ScheduleType = Literal["one_off", "interval", "cron"]
StatusType = Literal["pending", "dispatched", "cancelled"]


def _utcnow() -> datetime:
    """Return current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def _coerce_utc(dt: datetime | float | None) -> Optional[datetime]:
    """
    Ensure the value is timezone-aware UTC datetime.
    Accepts:
    - datetime
    - float/int (unix timestamp)
    """
    if dt is None:
        return None
    if isinstance(dt, (float, int)):
        return datetime.fromtimestamp(dt, tz=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class ScheduledTaskReference:
    """
    User-facing, high-level schedule declaration produced by `.schedule()`.

    Instances of this class are lightweight and may be ephemeral; the backend
    will convert them into durable `ScheduleEnvelope` records for persistence.

    Attributes
    ----------
    id : str
        Client-provided or auto-generated UUID for traceability. Optional.
    func_name : str
        Name of the registered Nuvom task to execute.
    args : List[Any]
        Positional arguments to pass to the task function.
    kwargs : Dict[str, Any]
        Keyword arguments to pass to the task function.
    schedule_type : Literal["one_off","interval","cron"]
        The kind of schedule being requested.
    next_run : Optional[datetime]
        First execution timestamp (UTC). Required for one-off; optional for
        interval/cron (dispatcher/backends can compute first run if omitted).
    interval_secs : Optional[int]
        Fixed interval in seconds for repeating schedules.
    cron_expr : Optional[str]
        Cron expression for cron schedules. (Parsing occurs later.)
    timezone : str
        IANA timezone string for cron evaluation. Defaults to "UTC".
    priority : int
        Desired priority when the actual execution job is pushed to the main
        queue. Lower means higher priority (consistent with many queue systems).
    metadata : Dict[str, Any]
        Free-form metadata that backends/dispatchers may leverage.
    created_at : float
        UNIX timestamp at creation time (seconds).
    """

    func_name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    schedule_type: ScheduleType = "one_off"
    next_run: Optional[datetime] = None
    interval_secs: Optional[int] = None
    cron_expr: Optional[str] = None
    timezone: str = "UTC"

    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)

    # ---------------------------- factory methods ----------------------------

    @classmethod
    def create(
        cls,
        *,
        func_name: str,
        args: List[Any] | None = None,
        kwargs: Dict[str, Any] | None = None,
        schedule_type: ScheduleType,
        next_run: Optional[datetime] = None,
        interval_secs: Optional[int] = None,
        cron_expr: Optional[str] = None,
        timezone: str = "UTC",
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
    ) -> "ScheduledTaskReference":
        """
        Construct a `ScheduledTaskReference` with basic validation.

        Parameters
        ----------
        func_name : str
            Registered task name to execute.
        args, kwargs : Optional
            Payload passed to the task at dispatch time.
        schedule_type : Literal["one_off","interval","cron"]
            Desired schedule category.
        next_run : Optional[datetime]
            First execution time in UTC. Required for one-off schedules.
        interval_secs : Optional[int]
            Interval length in seconds for repeating schedules.
        cron_expr : Optional[str]
            Cron expression used for cron schedules.
        timezone : str
            Timezone used for cron evaluation. Defaults to "UTC".
        priority : int
            Execution priority for the *actual* Job enqueued later.
        metadata : Optional[Dict[str, Any]]
            Free-form additional information (e.g., idempotency keys).
        id : Optional[str]
            Optional client-provided UUID for traceability.

        Returns
        -------
        ScheduledTaskReference
            Validated reference object ready to be enqueued into a backend.

        Raises
        ------
        ValueError
            If schedule parameters are inconsistent or missing.
        """
        args = list(args or [])
        kwargs = dict(kwargs or {})
        next_run = _coerce_utc(next_run)

        if schedule_type == "one_off":
            if next_run is None:
                raise ValueError("`next_run` is required for one_off schedules.")
        elif schedule_type == "interval":
            if not interval_secs or interval_secs <= 0:
                raise ValueError("`interval_secs` must be > 0 for interval schedules.")
        elif schedule_type == "cron":
            if not cron_expr:
                raise ValueError("`cron_expr` is required for cron schedules.")
            # Note: actual cron parsing/validation occurs in dispatcher/backend.
        else:
            raise ValueError(f"Unsupported schedule_type: {schedule_type}")

        return cls(
            id=id or str(uuid.uuid4()),
            func_name=func_name,
            args=args,
            kwargs=kwargs,
            schedule_type=schedule_type,
            next_run=next_run,
            interval_secs=interval_secs,
            cron_expr=cron_expr,
            timezone=timezone or "UTC",
            priority=int(priority),
            metadata=metadata or {},
        )

    # ---------------------------- transformations ---------------------------

    def to_envelope(self) -> "ScheduleEnvelope":
        """
        Convert this reference into a backend-friendly `ScheduleEnvelope`.

        The envelope is durable and includes fields the backend needs for
        persistence and dispatch bookkeeping.
        """
        next_run_ts = (
            float(self.next_run.timestamp()) if self.next_run is not None else None
        )
        return ScheduleEnvelope(
            id=self.id,
            task_name=self.func_name,
            args=self.args,
            kwargs=self.kwargs,
            schedule_type=self.schedule_type,
            next_run_ts=next_run_ts,
            interval_secs=self.interval_secs,
            cron_expr=self.cron_expr,
            timezone=self.timezone,
            priority=self.priority,
            metadata=dict(self.metadata),
            status="pending",
            run_count=0,
            created_at=self.created_at,
            updated_at=time.time(),
        )


@dataclass
class ScheduleEnvelope:
    """
    Backend-facing durable record for a scheduled execution.

    Attributes
    ----------
    id : str
        Unique schedule identifier (UUID).
    task_name : str
        Registered task name to execute when due.
    args : List[Any]
        Positional payload passed to the task.
    kwargs : Dict[str, Any]
        Keyword payload passed to the task.
    schedule_type : Literal["one_off","interval","cron"]
        Type of schedule.
    next_run_ts : Optional[float]
        Next execution time as UNIX timestamp (UTC seconds).
    interval_secs : Optional[int]
        Interval (seconds) for interval schedules.
    cron_expr : Optional[str]
        Cron expression for cron schedules.
    timezone : str
        IANA timezone used for cron evaluation.
    priority : int
        Priority for enqueuing into the main execution queue.
    metadata : Dict[str, Any]
        Free-form structured metadata.
    status : Literal["pending","dispatched","cancelled"]
        Current lifecycle state.
    run_count : int
        Number of dispatches performed (useful for recurring).
    created_at : float
        UNIX timestamp (seconds) when envelope was created.
    updated_at : float
        UNIX timestamp (seconds) when envelope was last modified.
    """

    id: str
    task_name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    schedule_type: ScheduleType = "one_off"
    next_run_ts: Optional[float] = None
    interval_secs: Optional[int] = None
    cron_expr: Optional[str] = None
    timezone: str = "UTC"

    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    status: StatusType = "pending"
    run_count: int = 0

    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # ------------------------------- helpers --------------------------------

    def mark_dispatched(self) -> None:
        """Transition to 'dispatched' and bump counters/timestamps."""
        self.status = "dispatched"
        self.run_count += 1
        self.updated_at = time.time()

    def cancel(self) -> None:
        """Transition to 'cancelled' safely."""
        self.status = "cancelled"
        self.updated_at = time.time()

    def is_due(self, now_ts: Optional[float] = None) -> bool:
        """
        Return True if this envelope is due to run at `now_ts`.

        Parameters
        ----------
        now_ts : Optional[float]
            UNIX timestamp to evaluate against. Defaults to current time.
        """
        if self.status != "pending":
            return False
        if self.next_run_ts is None:
            return False
        now_ts = now_ts if now_ts is not None else time.time()
        return self.next_run_ts <= now_ts

    def schedule_next(self, now_ts: Optional[float] = None) -> None:
        """
        Compute and set the next `next_run_ts` for recurring schedules.

        - For `interval`, adds `interval_secs` repeatedly until strictly future.
        - For `cron`, this method is a placeholder; cron evaluation is handled
          by the dispatcher (which has the cron parsing dependency).
        - For `one_off`, clears `next_run_ts` (no next occurrence).

        The method updates `updated_at`.
        """
        self.updated_at = time.time()
        if self.schedule_type == "one_off":
            self.next_run_ts = None
            return

        now_ts = now_ts if now_ts is not None else time.time()

        if self.schedule_type == "interval":
            if not self.interval_secs or self.interval_secs <= 0:
                raise ValueError("interval_secs must be > 0 for interval schedules.")
            # ensure strictly in the future
            base = self.next_run_ts or now_ts
            n = max(1, int((now_ts - base) // self.interval_secs) + 1)
            self.next_run_ts = float(base + n * self.interval_secs)
            return

        if self.schedule_type == "cron":
            # Dispatcher will compute next cron run and set next_run_ts.
            # Keeping logic centralized avoids importing cron libraries here.
            return
