# nuvom/scheduler/memory_queue.py

"""
In-memory Scheduler Backend
===========================

A development/testing backend that keeps schedules in process memory.
Implements the `SchedulerBackend` interface defined in `backend.py`.

Notes:
------
- Non-persistent: all schedules are lost when the process restarts.
- Thread-safe for concurrent enqueue/list/due operations.
- Uses a min-heap keyed by `next_run_ts` for efficient due lookups.
"""

from __future__ import annotations

import heapq
import threading
import time
from typing import Dict, List, Optional, Tuple

from nuvom.scheduler.backend import SchedulerBackend
from nuvom.scheduler.models import ScheduledTaskReference, ScheduleEnvelope


class InMemorySchedulerBackend(SchedulerBackend):
    """
    In-memory scheduler backend.

    This backend:
    - Stores envelopes in a dictionary for O(1) lookups by ID.
    - Maintains a heap of `(next_run_ts, id)` for efficient due queries.
    - Is safe for concurrent access within a single process.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._envelopes: Dict[str, ScheduleEnvelope] = {}
        self._heap: List[Tuple[float, str]] = []

    # ----------------------------------------------------------------------
    # Write path
    # ----------------------------------------------------------------------

    def enqueue(self, ref: ScheduledTaskReference) -> ScheduleEnvelope:
        """
        Store a new scheduled task in memory.

        Parameters
        ----------
        ref : ScheduledTaskReference
            Reference produced by Task.schedule().

        Returns
        -------
        ScheduleEnvelope
            Durable envelope stored in backend.
        """
        envelope = ref.to_envelope()
        with self._lock:
            self._envelopes[envelope.id] = envelope
            if envelope.next_run_ts is not None:
                heapq.heappush(self._heap, (envelope.next_run_ts, envelope.id))
        return envelope

    # ----------------------------------------------------------------------
    # Read path
    # ----------------------------------------------------------------------

    def get(self, schedule_id: str) -> Optional[ScheduleEnvelope]:
        """Retrieve a schedule envelope by ID."""
        with self._lock:
            return self._envelopes.get(schedule_id)

    def list(self) -> List[ScheduleEnvelope]:
        """Return all envelopes currently stored."""
        with self._lock:
            return list(self._envelopes.values())

    def due(self, now_ts: Optional[float] = None, limit: Optional[int] = None) -> List[ScheduleEnvelope]:
        """
        Return all envelopes that are due to run at `now_ts`.

        Parameters
        ----------
        now_ts : Optional[float]
            Timestamp (seconds) to evaluate. Defaults to current time.
        limit : Optional[int]
            Maximum number of envelopes to return.

        Returns
        -------
        List[ScheduleEnvelope]
            List of envelopes ready for dispatch.
        """
        now_ts = now_ts or time.time()
        due_list: List[ScheduleEnvelope] = []

        with self._lock:
            while self._heap and self._heap[0][0] <= now_ts:
                _, sid = heapq.heappop(self._heap)
                env = self._envelopes.get(sid)
                if env is None or env.status != "pending":
                    continue
                due_list.append(env)
                if limit and len(due_list) >= limit:
                    break

        return due_list

    # ----------------------------------------------------------------------
    # Lifecycle operations
    # ----------------------------------------------------------------------

    def ack_dispatched(self, schedule_id: str) -> None:
        """
        Mark a schedule as dispatched and increment its run count.
        """
        with self._lock:
            env = self._envelopes.get(schedule_id)
            if env:
                env.mark_dispatched()

    def reschedule(self, schedule_id: str, next_run_ts: float) -> None:
        """
        Update the `next_run_ts` for a given schedule.
        """
        with self._lock:
            env = self._envelopes.get(schedule_id)
            if not env:
                return
            env.next_run_ts = next_run_ts
            env.status = "pending"
            env.updated_at = time.time()
            heapq.heappush(self._heap, (next_run_ts, schedule_id))

    def cancel(self, schedule_id: str) -> None:
        """
        Cancel a pending schedule.
        """
        with self._lock:
            env = self._envelopes.get(schedule_id)
            if env:
                env.cancel()
                # Heap cleanup is lazy; entry ignored on pop.

    # ----------------------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------------------

    def _clear(self) -> None:
        """
        Clear all schedules. For testing only.
        """
        with self._lock:
            self._envelopes.clear()
            self._heap.clear()
