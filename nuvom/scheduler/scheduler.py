# nuvom/scheduler/scheduler.py

"""
Nuvom Scheduler Engine
======================

This module implements the `Scheduler` class, which is responsible for managing
ScheduledJob definitions and enqueuing them as high-priority Nuvom Jobs when due.

The scheduler is designed with the following philosophy:
1. **Separation of concerns**: Scheduler never executes tasks; it only enqueues
   jobs into the Nuvom queue for worker execution.
2. **Priority handling**: Scheduled jobs are enqueued with high priority to
   ensure they are executed promptly relative to ad-hoc tasks.
3. **Persistence**: Schedule definitions are persisted via a `SchedulerStore`
   implementation, allowing recovery and continuity across restarts.
4. **Recurring schedules**: Cron and interval schedules are automatically
   recomputed after dispatch.
5. **One-off schedules**: Automatically disabled after being enqueued.
6. **Thread-safe**: Public API methods are safe to call concurrently.

Core responsibilities:
- Maintain an in-memory min-heap of schedules sorted by `next_run_ts`.
- Poll due schedules at configurable granularity.
- Handle misfires according to schedule policies.
- Convert `ScheduledJob` instances into `Job` objects and enqueue them with
  high priority for uniform worker execution.
"""

from __future__ import annotations

import heapq
import threading
import time
from typing import Dict, Optional, Tuple, List

from nuvom.log import get_logger
from nuvom.scheduler.model import ScheduledJob
from nuvom.scheduler.store import SchedulerStore
from nuvom.queue import enqueue
from nuvom.job import Job

logger = get_logger()


class Scheduler:
    """
    Scheduler engine for enqueuing due `ScheduledJob`s as high-priority Nuvom Jobs.

    This class handles the lifecycle, persistence synchronization, and polling
    loop for scheduled jobs. It does **not execute tasks** directly; instead,
    it converts schedules into jobs and enqueues them using the Nuvom queue
    system, maintaining a consistent execution path for all tasks.

    Attributes
    ----------
    store : SchedulerStore
        Persistent store used to save/load schedule definitions.
    _tick : float
        Minimum polling interval (seconds) when no tasks are scheduled.
    _heap : list[tuple[float, str]]
        Min-heap of (next_run_ts, schedule_id) tuples.
    _jobs_by_id : dict[str, ScheduledJob]
        Lookup of ScheduledJob instances by their schedule ID.
    _lock : threading.RLock
        Recursive lock for thread-safe operations.
    _thread : Optional[threading.Thread]
        Background thread for running the scheduler loop.
    _stop_event : threading.Event
        Event used to signal stopping of the scheduler loop.
    _wakeup_event : threading.Event
        Event used to interrupt sleep for immediate schedule processing.
    """

    def __init__(self, store: SchedulerStore, tick_granularity: float = 60.0) -> None:
        """
        Initialize the Scheduler.

        Parameters
        ----------
        store : SchedulerStore
            The persistent store for schedule definitions.
        tick_granularity : float, optional
            Minimum polling interval in seconds when no schedules are due (default=60.0).
        """
        self.store = store
        self._tick = float(tick_granularity)

        self._heap: List[Tuple[float, str]] = []
        self._jobs_by_id: Dict[str, ScheduledJob] = {}

        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._wakeup_event = threading.Event()

    # ---------------------------- lifecycle ---------------------------------
    def start(self, background: bool = True) -> None:
        """
        Start the scheduler loop.

        Parameters
        ----------
        background : bool, optional
            If True (default), run loop in a background daemon thread.
            Otherwise, block the current thread.
        """
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.debug("Scheduler already running")
                return

            self._load_from_store()
            self._stop_event.clear()
            if background:
                self._thread = threading.Thread(
                    target=self._run_loop,
                    name="NuvomScheduler",
                    daemon=True,
                )
                self._thread.start()
            else:
                self._run_loop()

    def stop(self, timeout: Optional[float] = None) -> None:
        """
        Stop the scheduler loop.

        Parameters
        ----------
        timeout : Optional[float]
            Maximum seconds to wait for the background thread to exit.
        """
        with self._lock:
            self._stop_event.set()
            self._wakeup_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                logger.info("Scheduler stopped")

    # ---------------------------- store sync -------------------------------
    def _load_from_store(self) -> None:
        """
        Load all schedules from the persistent store and rebuild the in-memory heap.

        - Computes `next_run_ts` if missing.
        - Applies misfire policies for schedules that are overdue.
        - Initializes heap and job lookup.
        """
        logger.debug("Loading schedules from store")
        with self._lock:
            self._heap.clear()
            self._jobs_by_id.clear()
            for s in self.store.list_all():
                if not s.enabled:
                    continue

                try:
                    if s.next_run_ts is None:
                        s.next_run_ts = s.compute_next_run_ts()
                except Exception as e:
                    logger.error("Failed computing next_run_ts for %s: %s", s.id, e)
                    continue

                now = time.time()
                if s.next_run_ts and s.next_run_ts < now:
                    self._handle_misfire(s, now)

                self._push_schedule(s)
                self._jobs_by_id[s.id] = s

            logger.info("Loaded %d schedules", len(self._jobs_by_id))

    # ---------------------------- public API -------------------------------
    def add_schedule(self, job: ScheduledJob) -> ScheduledJob:
        """
        Persist and register a new schedule.

        Parameters
        ----------
        job : ScheduledJob
            The schedule definition to add.

        Returns
        -------
        ScheduledJob
            Stored schedule (may have assigned ID or modified fields).
        """
        with self._lock:
            stored = self.store.add(job)
            stored.next_run_ts = stored.compute_next_run_ts()
            stored.touch_updated()
            self._jobs_by_id[stored.id] = stored
            self._push_schedule(stored)
            self._wakeup_event.set()
            logger.info("Added schedule %s -> next=%s", stored.id, stored.next_run_ts)
            return stored

    def update_schedule(self, job: ScheduledJob) -> None:
        """
        Update an existing schedule in the store and heap.

        Parameters
        ----------
        job : ScheduledJob
            The schedule definition to update.
        """
        with self._lock:
            self.store.update(job)
            job.touch_updated()
            self._jobs_by_id[job.id] = job
            self._rebuild_heap()
            self._wakeup_event.set()
            logger.info("Updated schedule %s", job.id)

    def remove_schedule(self, schedule_id: str) -> None:
        """
        Remove a schedule by ID.

        Parameters
        ----------
        schedule_id : str
            The schedule ID to remove.
        """
        with self._lock:
            self.store.remove(schedule_id)
            self._jobs_by_id.pop(schedule_id, None)
            self._rebuild_heap()
            self._wakeup_event.set()
            logger.info("Removed schedule %s", schedule_id)

    def list_schedules(self) -> List[ScheduledJob]:
        """
        List all registered schedules.

        Returns
        -------
        list[ScheduledJob]
        """
        with self._lock:
            return list(self._jobs_by_id.values())

    def enable_schedule(self, schedule_id: str) -> None:
        """
        Enable a previously disabled schedule.

        Parameters
        ----------
        schedule_id : str
            The schedule ID to enable.

        Raises
        ------
        KeyError
            If the schedule ID does not exist.
        """
        with self._lock:
            s = self.store.get(schedule_id)
            if not s:
                raise KeyError(schedule_id)
            s.enabled = True
            s.next_run_ts = s.compute_next_run_ts()
            s.touch_updated()
            self.store.update(s)
            self._jobs_by_id[s.id] = s
            self._push_schedule(s)
            self._wakeup_event.set()

    def disable_schedule(self, schedule_id: str) -> None:
        """
        Disable an active schedule.

        Parameters
        ----------
        schedule_id : str
            The schedule ID to disable.

        Raises
        ------
        KeyError
            If the schedule ID does not exist.
        """
        with self._lock:
            s = self.store.get(schedule_id)
            if not s:
                raise KeyError(schedule_id)
            s.enabled = False
            s.touch_updated()
            self.store.update(s)
            self._jobs_by_id.pop(schedule_id, None)
            self._rebuild_heap()
            self._wakeup_event.set()

    def run_once_now(self, schedule_id: str) -> Optional[str]:
        """
        Immediately enqueue a schedule as a high-priority job.

        Parameters
        ----------
        schedule_id : str
            The schedule ID to run.

        Returns
        -------
        Optional[str]
            The Job ID of the enqueued job, or None on failure.

        Raises
        ------
        KeyError
            If the schedule ID does not exist.
        """
        with self._lock:
            s = self._jobs_by_id.get(schedule_id) or self.store.get(schedule_id)
            if not s:
                raise KeyError(schedule_id)

            job = Job(
                func_name=s.task_name,
                args=s.args,
                kwargs=s.kwargs,
                scheduled=True,
                priority=1,
            )
            enqueue(job)
            return getattr(job, "id", None)

    # ---------------------------- internal heap ---------------------------
    def _push_schedule(self, s: ScheduledJob) -> None:
        """Insert a schedule into the in-memory heap."""
        if s.next_run_ts is None:
            return
        heapq.heappush(self._heap, (float(s.next_run_ts), s.id))

    def _rebuild_heap(self) -> None:
        """Rebuild the heap from all enabled schedules."""
        self._heap = []
        for s in self._jobs_by_id.values():
            if s.enabled and s.next_run_ts:
                heapq.heappush(self._heap, (float(s.next_run_ts), s.id))

    def _pop_due(self, until_ts: float) -> List[ScheduledJob]:
        """
        Pop all schedules due up to `until_ts`.

        Parameters
        ----------
        until_ts : float
            Unix timestamp (seconds) up to which schedules are considered due.

        Returns
        -------
        list[ScheduledJob]
        """
        due = []
        while self._heap and self._heap[0][0] <= until_ts:
            _, sid = heapq.heappop(self._heap)
            s = self._jobs_by_id.get(sid)
            if s and s.enabled:
                due.append(s)
        return due

    # ---------------------------- misfire handling ------------------------
    def _handle_misfire(self, s: ScheduledJob, now: float) -> None:
        """
        Apply the misfire policy for overdue schedules.

        Parameters
        ----------
        s : ScheduledJob
            The overdue schedule.
        now : float
            Current Unix timestamp.
        """
        logger.warning(
            "Schedule %s missed (next_run=%s, now=%s) - policy=%s",
            s.id, s.next_run_ts, now, s.misfire_policy,
        )
        if s.misfire_policy == "run_immediately":
            return
        if s.misfire_policy == "skip":
            s.next_run_ts = s.compute_next_run_ts(from_ts=now)
            self.store.update(s)
        if s.misfire_policy == "reschedule":
            s.next_run_ts = now
            self.store.update(s)

    # ---------------------------- main loop -------------------------------
    def _run_loop(self) -> None:
        """
        Main scheduler loop.

        - Waits until the next schedule is due.
        - Pops due schedules and enqueues them as high-priority jobs.
        - Updates `next_run_ts` for recurring schedules.
        - Disables one-off schedules after enqueue.
        """
        logger.info("Scheduler loop started")
        while not self._stop_event.is_set():
            with self._lock:
                if not self._heap:
                    self._wakeup_event.clear()
                    timeout = self._tick
                else:
                    next_ts = self._heap[0][0]
                    now = time.time()
                    timeout = max(0.0, next_ts - now)

            # Wait until timeout or a wakeup event
            self._wakeup_event.wait(timeout=timeout)
            if self._stop_event.is_set():
                break
            self._wakeup_event.clear()

            now = time.time()
            with self._lock:
                due = self._pop_due(until_ts=now + 1e-6)

            for s in due:
                try:
                    job = Job(
                        func_name=s.task_name,
                        args=s.args,
                        kwargs=s.kwargs,
                        scheduled=True,
                        priority=1,
                    )
                    enqueue(job)
                    logger.info("Enqueued scheduled job for %s", s.id)
                except Exception as e:
                    logger.exception("Failed enqueuing schedule %s: %s", s.id, e)

                # Update next_run_ts for recurring schedules
                if s.schedule_type in ("interval", "cron"):
                    try:
                        s.next_run_ts = s.compute_next_run_ts(from_ts=time.time())
                        s.touch_updated()
                        self.store.update(s)
                        with self._lock:
                            self._push_schedule(s)
                    except Exception as e:
                        logger.exception("Failed updating next_run_ts for %s: %s", s.id, e)
                else:
                    # One-off schedule: disable after enqueue
                    s.enabled = False
                    s.touch_updated()
                    try:
                        self.store.update(s)
                    except Exception:
                        logger.exception("Failed disabling one-off schedule %s", s.id)

        logger.info("Scheduler loop exiting")
