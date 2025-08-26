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

import importlib
import threading
from abc import ABC, abstractmethod
from typing import List, Optional

from nuvom.scheduler.models import ScheduledTaskReference, ScheduleEnvelope
from nuvom.config import get_settings

# -------------------------------------------------------------------------
# Abstract base class
# -------------------------------------------------------------------------
class SchedulerBackend(ABC):
    """
    Abstract base class for scheduler backends.
    Must be thread-safe and safe for concurrent workers.
    """

    # ----------------------------- write path ------------------------------
    @abstractmethod
    def enqueue(self, ref: ScheduledTaskReference) -> ScheduleEnvelope:
        """Persist a `ScheduledTaskReference` and return a `ScheduleEnvelope`."""
        raise NotImplementedError

    # ------------------------------ read path -----------------------------
    @abstractmethod
    def get(self, schedule_id: str) -> Optional[ScheduleEnvelope]:
        """Return an envelope by ID, or None if unknown."""
        raise NotImplementedError

    @abstractmethod
    def list(self) -> List[ScheduleEnvelope]:
        """List all stored schedule envelopes."""
        raise NotImplementedError

    @abstractmethod
    def due(self, now_ts: Optional[float] = None, limit: Optional[int] = None) -> List[ScheduleEnvelope]:
        """Return envelopes that are due for dispatch at the current timestamp."""
        raise NotImplementedError

    # ---------------------------- lifecycle ops ---------------------------
    @abstractmethod
    def ack_dispatched(self, schedule_id: str) -> None:
        """Mark an envelope as dispatched and increment run counters."""
        raise NotImplementedError

    @abstractmethod
    def reschedule(self, schedule_id: str, next_run_ts: float) -> None:
        """Update the `next_run_ts` for recurring schedules."""
        raise NotImplementedError

    @abstractmethod
    def cancel(self, schedule_id: str) -> None:
        """Cancel a pending scheduled task."""
        raise NotImplementedError


# -------------------------------------------------------------------------
# Backend loader & thread-safe singleton accessor
# -------------------------------------------------------------------------
_backend_singleton: Optional[SchedulerBackend] = None
_lock = threading.Lock()


def _load_backend() -> SchedulerBackend:
    """
    Dynamically load the backend specified in configuration.

    Supported values:
      - `sqlite` (default)
      - `memory`
      - `redis`
      - `package.module:ClassName` for custom implementations
    """
    settings = get_settings()
    backend_name = getattr(settings, "scheduler_backend", "sqlite").lower()

    if backend_name == "sqlite":
        from nuvom.scheduler.sqlite_backend import SqlSchedulerBackend
        return SqlSchedulerBackend()
    elif backend_name == "memory":
        from nuvom.scheduler.memory_backend import InMemorySchedulerBackend
        return InMemorySchedulerBackend()
    # elif backend_name == "redis":
    #     from nuvom.scheduler.redis_backend import RedisSchedulerBackend
    #     return RedisSchedulerBackend()

    # Load custom backend dynamically
    if ":" in backend_name:
        module_path, class_name = backend_name.split(":")
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        if not issubclass(cls, SchedulerBackend):
            raise TypeError(f"{class_name} is not a subclass of SchedulerBackend")
        return cls()

    raise ValueError(f"Unsupported scheduler backend: {backend_name}")


def set_scheduler_backend(backend: SchedulerBackend) -> None:
    """Explicitly set the global backend instance (used for tests or bootstrap)."""
    global _backend_singleton
    with _lock:
        _backend_singleton = backend


def get_scheduler_backend() -> SchedulerBackend:
    """
    Get the configured scheduler backend singleton.

    Loads the backend from settings if not already instantiated.
    Thread-safe for concurrent initialization.
    """
    global _backend_singleton
    if _backend_singleton is None:
        with _lock:
            if _backend_singleton is None:  # Double-checked locking
                _backend_singleton = _load_backend()
    return _backend_singleton
