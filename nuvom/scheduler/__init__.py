## nuvom/scheduler/__init__.py

"""
Nuvom Scheduler
===============

Public export surface for the scheduler subsystem.

This package provides:
- Data models for scheduled jobs and references.
- A pluggable backend interface and a default backend accessor.
- (In subsequent steps) an in-memory backend, dispatcher loop, and worker.

Typical usage
-------------
    from nuvom.scheduler import get_scheduler_backend
    from nuvom.scheduler.models import ScheduledTaskReference

    backend = get_scheduler_backend()
    ref = ScheduledTaskReference.create(
        func_name="send_email",
        args=["hello"],
        kwargs={"user_id": "42"},
        schedule_type="one_off",
        next_run=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    backend.enqueue(ref)

Notes
-----
The default backend accessor returns a singleton backend instance. In this
step we will wire it to an in-memory backend in `memory.py` (next file).
"""

from nuvom.scheduler.backend import get_scheduler_backend, SchedulerBackend
from nuvom.scheduler.models import ScheduledTaskReference, ScheduleEnvelope

__all__ = [
    "get_scheduler_backend",
    "SchedulerBackend",
    "ScheduledTaskReference",
    "ScheduleEnvelope",
]
