# nuvom/scheduler/backend.py

"""
Scheduler Backend Interface
===========================

This module defines the pluggable backend contract used by the scheduler
pipeline, plus a default backend accessor.

Responsibilities
----------------
- Persist incoming `ScheduledTaskReference` requests.
- Expose due `ScheduleEnvelope` records for dispatching.
- Provide basic lifecycle management (get, list, cancel, reschedule, ack).

This interface is intentionally minimal so that different storage engines
(in-memory, Redis, SQL) can be implemented without impacting the rest of
the system. The dispatcher (added in a later step) will depend only on
this contract.

Integration with Task.schedule()
--------------------------------
`Task.schedule()` should:
1) Build a `ScheduledTaskReference`
2) Call `get_scheduler_backend().enqueue(ref)`

The backend converts the reference to a `ScheduleEnvelope` and persists it.

Notes on priorities
-------------------
Backends do not execute tasks. They only store schedule metadata.
When a schedule is due, the dispatcher will convert it into a *regular*
`Job` and push it to the main execution queue with the envelope's priority.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Sequence

from nuvom.scheduler.models import ScheduledTaskReference, ScheduleEnvelope


class SchedulerBackend(ABC):
    """
    Abstract base class for scheduler backends.

    Any backend must be concurrency-safe for typical multi-threaded access.
    Stronger guarantees (e.g., distributed locks) are backend-specific.
    """

    # ----------------------------- write path ------------------------------

    @abstractmethod
    def enqueue(self, ref: ScheduledTaskReference) -> ScheduleEnvelope:
        """
        Persist a `ScheduledTaskReference` as a durable `ScheduleEnvelope`.

        Implementations should:
        - Validate and normalize inputs
        - Assign missing next_run_ts if appropriate (e.g., for interval/cron)
        - Ensure idempotency if metadata contains a unique key (optional)
        - Return the stored envelope
        """
        raise NotImplementedError

    # ------------------------------ read path -----------------------------

    @abstractmethod
    def get(self, schedule_id: str) -> Optional[ScheduleEnvelope]:
        """Return an envelope by id, or None if unknown."""
        raise NotImplementedError

    @abstractmethod
    def list(self) -> List[ScheduleEnvelope]:
        """Return all envelopes currently known to the backend."""
        raise NotImplementedError

    @abstractmethod
    def due(self, now_ts: Optional[float] = None, limit: Optional[int] = None) -> List[ScheduleEnvelope]:
        """
        Return envelopes that are due to run at `now_ts`.

        Implementations should not mutate envelopes here; the dispatcher
        will mark and/or reschedule after successful enqueue to the main queue.
        """
        raise NotImplementedError

    # ---------------------------- lifecycle ops ---------------------------

    @abstractmethod
    def ack_dispatched(self, schedule_id: str) -> None:
        """
        Mark an envelope as dispatched (successful handoff to main queue).

        Implementations should update status and bump run_count.
        """
        raise NotImplementedError

    @abstractmethod
    def reschedule(self, schedule_id: str, next_run_ts: float) -> None:
        """
        Update the next_run_ts for a schedule (cron/interval recomputation).
        """
        raise NotImplementedError

    @abstractmethod
    def cancel(self, schedule_id: str) -> None:
        """Cancel a pending schedule."""
        raise NotImplementedError


# -------------------------------------------------------------------------
# Default backend accessor
# -------------------------------------------------------------------------

_backend_singleton: Optional[SchedulerBackend] = None


def set_scheduler_backend(backend: SchedulerBackend) -> None:
    """
    Install a process-wide scheduler backend singleton.

    This is typically used by application bootstrap or tests.
    """
    global _backend_singleton
    _backend_singleton = backend


def get_scheduler_backend() -> SchedulerBackend:
    """
    Return the process-wide scheduler backend singleton.

    If no backend has been set yet, this function will lazily instantiate
    the in-memory backend implementation for convenience (dev/test).

    Production deployments should call `set_scheduler_backend(...)`
    during initialization to install a durable backend.
    """
    global _backend_singleton
    if _backend_singleton is None:
        # Lazy import to avoid circulars and heavy deps at import time.
        from nuvom.scheduler.sqlite_backend import SqlSchedulerBackend  # type: ignore
        _backend_singleton = SqlSchedulerBackend()
        
    return _backend_singleton # type: ignore
