# nuvom/scheduler/store.py

"""
Scheduler Store Abstractions.

This module defines the persistence layer contracts for scheduled jobs.
The Scheduler depends on a store to save, load, and update `ScheduledJob`
definitions. Different implementations (in-memory, SQLite, Redis, etc.)
can be provided without modifying the Scheduler logic.

Philosophy:
-----------
- Pluggable: stores are interchangeable via a simple Protocol interface.
- Minimal: only the core CRUD operations required by the Scheduler.
- Extensible: backends can add richer features (indexing, filtering, metrics).
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, List, Optional, Protocol

from nuvom.scheduler.model import ScheduledJob


class SchedulerStore(Protocol):
    """
    Protocol definition for scheduler persistence.

    Any implementation must support CRUD operations for `ScheduledJob`
    objects. The store is responsible for persisting scheduled jobs,
    ensuring they survive process restarts (for durable stores),
    and providing efficient access for the scheduler loop.

    Methods
    -------
    add(job: ScheduledJob) -> ScheduledJob:
        Insert a new scheduled job into the store.
    update(job: ScheduledJob) -> ScheduledJob:
        Update an existing scheduled job in the store.
    remove(job_id: str) -> None:
        Delete a scheduled job by ID.
    get(job_id: str) -> Optional[ScheduledJob]:
        Retrieve a scheduled job by ID, or None if not found.
    list_all() -> List[ScheduledJob]:
        Return all scheduled jobs currently in the store.
    """

    def add(self, job: ScheduledJob) -> ScheduledJob: ...
    def update(self, job: ScheduledJob) -> ScheduledJob: ...
    def remove(self, job_id: str) -> None: ...
    def get(self, job_id: str) -> Optional[ScheduledJob]: ...
    def list_all(self) -> List[ScheduledJob]: ...


class InMemorySchedulerStore:
    """
    In-memory scheduler store for development and testing.

    This implementation keeps jobs in a thread-safe dictionary
    (not durable across process restarts). Useful for:
      - Unit testing the Scheduler
      - Local prototyping
      - Demonstrating scheduling features without external dependencies

    Thread-safety:
    --------------
    - Uses a simple lock to ensure concurrent safety when
      adding, updating, or removing jobs.

    Example
    -------
    >>> store = InMemorySchedulerStore()
    >>> job = ScheduledJob(
    ...     id=str(uuid.uuid4()),
    ...     task_name="send_email",
    ...     schedule_type="interval",
    ...     interval_secs=60,
    ...     enabled=True,
    ...     created_at=time.time(),
    ...     updated_at=time.time(),
    ... )
    >>> store.add(job)
    >>> assert store.get(job.id) is not None
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, ScheduledJob] = {}
        self._lock = threading.Lock()

    def add(self, job: ScheduledJob) -> ScheduledJob:
        with self._lock:
            if job.id in self._jobs:
                raise ValueError(f"Job with id {job.id} already exists")
            self._jobs[job.id] = job
        return job

    def update(self, job: ScheduledJob) -> ScheduledJob:
        with self._lock:
            if job.id not in self._jobs:
                raise KeyError(f"Job with id {job.id} not found")
            self._jobs[job.id] = job
        return job

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def get(self, job_id: str) -> Optional[ScheduledJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_all(self) -> List[ScheduledJob]:
        with self._lock:
            return list(self._jobs.values())
