# nuvom/scheduler/__init__.py

"""
Nuvom Scheduler package public surface.

This package provides a pluggable scheduler implementation. The concrete
implementation modules are implemented in other files in the package.

Public API exported here:
- ScheduledJob (dataclass model)
- Scheduler (manager class)
- get_scheduler() (singleton accessor)
- store interfaces and concrete SQLite store
- decorators for declarative schedule registration

This file intentionally keeps the imports local to avoid importing heavy
modules during CLI startup until the scheduler is actually used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # type-only imports to keep runtime cost low
    from nuvom.scheduler.scheduler import Scheduler
    from nuvom.scheduler.model import ScheduledJob
    from nuvom.scheduler.store import PersistentStore


__all__ = [
    "ScheduledJob",
    "Scheduler",
    "get_scheduler",
    "PersistentStore",
    "SQLiteStore",
    "scheduled_task",
]

# Lightweight accessor (concrete implementation is imported lazily)
_scheduler_instance = None


def get_scheduler() -> "Scheduler":
    """Return the global Scheduler singleton, lazily created on first call.

    The concrete Scheduler class is imported when needed, keeping the
    package import lightweight for commands that don't use scheduling.
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        # Local import to avoid startup costs when CLI isn't starting scheduler
        from nuvom.scheduler.scheduler import Scheduler
        from nuvom.scheduler.sqlite_store import SQLiteStore

        store = SQLiteStore()
        _scheduler_instance = Scheduler(store=store)
    return _scheduler_instance


# Re-export decorator and store symbol names lazily
def scheduled_task(*args, **kwargs):
    from .decorators import scheduled_task as _decor

    return _decor(*args, **kwargs)


# Expose SQLiteStore symbol without importing heavy modules at top-level
def SQLiteStore(*args, **kwargs):
    from .sqlite_store import SQLiteStore as _SQLiteStore

    return _SQLiteStore(*args, **kwargs)
