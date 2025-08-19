# nuvom/scheduler/model.py

"""
Scheduler data model
====================

This module defines the canonical `ScheduledJob` data model used by the
Nuvom scheduler. This model is intentionally feature-complete.

- id: str (UUID)
- task_name: str (registered task)
- schedule_type: Literal["cron","interval","once"]
- cron_expr: Optional[str]
- interval_secs: Optional[int]
- run_at: Optional[float] (unix timestamp)
- args, kwargs: default args for created Jobs
- enabled: bool
- next_run_ts: Optional[float]
- timezone: Optional[str] (default UTC)
- misfire_policy: Literal["run_immediately","skip","reschedule"]
- concurrency_limit: Optional[int]
- queue_name: Optional[str]
- created_at, updated_at: float (unix timestamps)

The model includes helpers for validation, computing the next run timestamp
(for interval & cron schedules) and serialization helpers for persistence.

Notes
-----
- Cron expression handling is implemented via `croniter` when available. If
  `croniter` is not installed and a cron schedule is used, `compute_next_run_ts`
  will raise a clear error explaining the missing dependency.
- Time values are stored as UNIX timestamps (floats) in UTC to keep storage
  simple and interoperable across environments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal
import time
import uuid

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - zoneinfo available on py3.9+
    ZoneInfo = None

# croniter is optional; used only for cron schedule computation
try:
    from croniter import croniter
except Exception:  # pragma: no cover - import handled at runtime
    croniter = None


@dataclass
class ScheduledJob:
    """
    Canonical representation of a scheduled task definition.

    This structure is intentionally storage-friendly (all datatypes are
    JSON/SQLite serializable) and contains the necessary metadata to
    persist, compute scheduling, and enforce simple runtime policies.

    Attributes
    ----------
    id : str
        Unique UUID string for the schedule entry.
    task_name : str
        Registered task name (looked up via the task registry at runtime).
    schedule_type : Literal["cron", "interval", "once"]
        One of 'cron', 'interval', or 'once'. Defines how `next_run_ts` is
        computed.
    cron_expr : Optional[str]
        Cron expression (only used when schedule_type == 'cron').
    interval_secs : Optional[int]
        Interval length in seconds (only used when schedule_type == 'interval').
    run_at : Optional[float]
        Unix timestamp for one-off schedules (schedule_type == 'once').
    args : List[Any]
        Positional arguments applied to the created Job.
    kwargs : Dict[str, Any]
        Keyword arguments applied to the created Job.
    enabled : bool
        Whether the schedule is active. Disabled schedules are ignored by the
        scheduler loop.
    next_run_ts : Optional[float]
        Pre-computed timestamp (unix float) for the next run. This is stored
        and persisted so restarts can resume without recomputing state.
    timezone : Optional[str]
        Timezone name (IANA) used for cron evaluation. Defaults to 'UTC'.
    misfire_policy : Literal['run_immediately','skip','reschedule']
        Behavior when a scheduled time was missed (e.g., scheduler was down).
    concurrency_limit : Optional[int]
        If set, the maximum number of concurrently running jobs for this
        scheduled entry.
    queue_name : Optional[str]
        Optional queue target (reserved for future multi-queue support).
    created_at : float
        Creation timestamp (unix float).
    updated_at : float
        Last-updated timestamp (unix float).
    """

    # Core identity
    task_name: str
    schedule_type: Literal["cron", "interval", "once"]

    # Scheduling parameters
    cron_expr: Optional[str] = None
    interval_secs: Optional[int] = None
    run_at: Optional[float] = None

    # Execution defaults
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # Runtime / policy
    enabled: bool = True
    next_run_ts: Optional[float] = None
    timezone: Optional[str] = "UTC"
    misfire_policy: Literal["run_immediately", "skip", "reschedule"] = "run_immediately"
    concurrency_limit: Optional[int] = None
    queue_name: Optional[str] = None

    # Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # ----------------------------- validation -----------------------------
    def __post_init__(self) -> None:
        """Validate mutually exclusive/required fields and coerce defaults."""
        valid_types = {"cron", "interval", "once"}
        if self.schedule_type not in valid_types:
            raise ValueError(f"Invalid schedule_type: {self.schedule_type}")

        if self.schedule_type == "cron":
            if not self.cron_expr:
                raise ValueError("cron_expr is required for schedule_type='cron'")
            if not croniter:
                # Defer to runtime error in compute_next_run_ts but warn early
                raise RuntimeError(
                    "cron schedules require the 'croniter' package. Install via: pip install croniter"
                )

        if self.schedule_type == "interval":
            if not self.interval_secs or self.interval_secs <= 0:
                raise ValueError("interval_secs must be a positive integer for 'interval' schedules")

        if self.schedule_type == "once":
            if not self.run_at:
                raise ValueError("run_at (unix timestamp) is required for 'once' schedules")

        # Ensure timezone validity when zoneinfo is available
        if self.timezone and ZoneInfo is not None:
            try:
                ZoneInfo(self.timezone)
            except Exception:
                raise ValueError(f"Invalid timezone: {self.timezone}")

        # If next_run_ts is not provided, compute a best-effort next run
        if self.next_run_ts is None:
            self.next_run_ts = self.compute_next_run_ts(from_ts=time.time())

    # -------------------------- scheduling helpers ------------------------
    def compute_next_run_ts(self, from_ts: Optional[float] = None) -> Optional[float]:
        """
        Compute the next run timestamp for this schedule.

        Parameters
        ----------
        from_ts : Optional[float]
            Base timestamp to compute from (defaults to now).

        Returns
        -------
        Optional[float]
            Unix timestamp for the next run, or None for malformed schedules.

        Notes
        -----
        - For `once` schedules, this returns `run_at` (even if it is in the past).
        - For `interval` schedules, this computes the next occurrence >= `from_ts`.
        - For `cron` schedules, this uses `croniter` to compute the next occurrence
          in the configured timezone.
        """
        now = from_ts or time.time()

        if self.schedule_type == "once":
            return float(self.run_at) if self.run_at is not None else None

        if self.schedule_type == "interval":
            base = self.next_run_ts or self.run_at or now
            # if base is None (shouldn't happen), use now
            if base is None:
                base = now
            # advance in multiples of interval until >= now
            interval = float(self.interval_secs)
            if interval <= 0:
                raise ValueError("interval_secs must be > 0")

            # compute next occurrence without looping when possible
            if base >= now:
                return float(base)

            # n = ceil((now - base) / interval)
            delta = now - base
            n = int(delta // interval) + 1
            return float(base + n * interval)

        if self.schedule_type == "cron":
            if not croniter:
                raise RuntimeError("cron schedule requires 'croniter' package")

            # croniter accepts float start_time and returns next as float
            # Respect timezone if ZoneInfo is available
            try:
                start = now
                it = croniter(self.cron_expr, start)
                nxt = it.get_next(float)
                return float(nxt)
            except Exception as e:
                raise RuntimeError(f"Failed to compute next cron run: {e}")

        # Fallback: unknown schedule type
        return None

    # --------------------------- utility methods -------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the ScheduledJob to a JSON-friendly dict."""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "schedule_type": self.schedule_type,
            "cron_expr": self.cron_expr,
            "interval_secs": self.interval_secs,
            "run_at": self.run_at,
            "args": self.args,
            "kwargs": self.kwargs,
            "enabled": self.enabled,
            "next_run_ts": self.next_run_ts,
            "timezone": self.timezone,
            "misfire_policy": self.misfire_policy,
            "concurrency_limit": self.concurrency_limit,
            "queue_name": self.queue_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledJob":
        """Create a ScheduledJob from a dict (reverse of `to_dict`)."""
        # avoid passing None for default fields implicitly
        kwargs = dict(
            id=data.get("id") or str(uuid.uuid4()),
            task_name=data["task_name"],
            schedule_type=data["schedule_type"],
            cron_expr=data.get("cron_expr"),
            interval_secs=data.get("interval_secs"),
            run_at=data.get("run_at"),
            args=data.get("args") or [],
            kwargs=data.get("kwargs") or {},
            enabled=data.get("enabled", True),
            next_run_ts=data.get("next_run_ts"),
            timezone=data.get("timezone", "UTC"),
            misfire_policy=data.get("misfire_policy", "run_immediately"),
            concurrency_limit=data.get("concurrency_limit"),
            queue_name=data.get("queue_name"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
        return cls(**kwargs)

    def touch_updated(self) -> None:
        """Update the `updated_at` timestamp to now."""
        self.updated_at = time.time()

