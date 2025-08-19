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
    from nuvom.scheduler.scheduler import Scheduler
    from nuvom.scheduler.model import ScheduledJob
    from nuvom.scheduler.store import SchedulerStore

__all__ = [
    "ScheduledJob",
    "Scheduler",
    "get_scheduler",
    "SchedulerStore",
    "SQLiteStore",
    "scheduled_task",
]

# ------------------------ Singleton ------------------------
_scheduler_instance: Scheduler | None = None

def get_scheduler() -> "Scheduler":
    """
    Return the global Scheduler singleton, lazily created on first call.

    Uses SQLiteStore as the default persistent backend.
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        from nuvom.scheduler.scheduler import Scheduler
        from nuvom.scheduler.sqlite_store import SQLiteStore

        store = SQLiteStore()  # default path 'nuvom_scheduler.db'
        _scheduler_instance = Scheduler(store=store)
    return _scheduler_instance

# ------------------------ Re-exports ------------------------
def scheduled_task(*args, **kwargs):
    from nuvom.scheduler.decorators import scheduled_task as _decor
    return _decor(*args, **kwargs)

def SQLiteStore(*args, **kwargs):
    from nuvom.scheduler.sqlite_store import SQLiteStore as _SQLiteStore
    return _SQLiteStore(*args, **kwargs)
