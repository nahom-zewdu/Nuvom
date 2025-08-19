# nuvom/scheduler/scheduler.py

"""
Scheduler core engine
=====================

This module implements the Scheduler class - the runtime engine responsible for
managing ScheduledJob definitions, computing next-run timestamps, and creating
Nuvom Job instances at the scheduled times.

Primary responsibilities:
- Maintain an in-memory min-heap ordered by `next_run_ts` for efficient wake-ups.
- Persist schedule definitions through a provided `SchedulerStore` implementation.
- Offer a clear, testable public API: add/update/remove/list/enable/disable/run_now.
- Run a single-threaded event loop that sleeps until the next schedule is due
  and dispatches jobs atomically.

Design notes:
- This core is intentionally backend-agnostic. Concurrency, persistence, and
  distributed coordination are delegated to the provided store and optional
  lock implementations (e.g. Redis) which can be hooked in later.
- The Scheduler uses `ScheduledJob.compute_next_run_ts()` to compute the next
  occurrence for cron/interval schedules. Cron schedules require `croniter`.

Safety & failure handling:
- On startup the scheduler loads persisted schedules and recomputes/validates
  `next_run_ts`. Missed runs (misfires) are handled according to each schedule's
  `misfire_policy`.
- All public methods are thread-safe.

"""

from __future__ import annotations

import heapq
import threading
import time
from typing import Dict, Optional, Tuple, List

from nuvom.log import get_logger
from nuvom.scheduler.model import ScheduledJob
from nuvom.scheduler.store import SchedulerStore
from nuvom.task import get_task

logger = get_logger()


class Scheduler:
    """
    Scheduler engine that orchestrates ScheduledJob execution.

    Parameters
    ----------
    store: SchedulerStore
        Persistent store used to save and load ScheduledJob definitions.
    tick_granularity: float
        Minimum sleep granularity in seconds used when no tasks are scheduled.
    """

    def __init__(self, store: SchedulerStore, tick_granularity: float = 60.0) -> None:
        self.store = store
        self._tick = float(tick_granularity)

        # In-memory structures
        # _heap contains tuples (next_run_ts, schedule_id)
        self._heap: List[Tuple[float, str]] = []
        self._jobs_by_id: Dict[str, ScheduledJob] = {}

        # Concurrency & lifecycle
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._wakeup_event = threading.Event()

        # Runtime counters
        self._running_counts: Dict[str, int] = {}

    # ---------------------------- lifecycle ---------------------------------
    def start(self, background: bool = True) -> None:
        """
        Start the scheduler loop. If `background` is True (default) the loop
        runs on a daemon thread; otherwise it runs on the current thread.
        """
        with self._lock:
            if self._thread and self._thread.is_alive():
                logger.debug("Scheduler already running")
                return

            # Load persisted schedules
            self._load_from_store()

            self._stop_event.clear()
            if background:
                self._thread = threading.Thread(target=self._run_loop, name="NuvomScheduler", daemon=True)
                self._thread.start()
            else:
                self._run_loop()

    def stop(self, timeout: Optional[float] = None) -> None:
        """
        Signal the scheduler to stop and wait up to `timeout` seconds for the
        background thread to exit. If no thread is running this is a no-op.
        """
        with self._lock:
            self._stop_event.set()
            self._wakeup_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                logger.info("Scheduler stopped")

    # ---------------------------- store sync -------------------------------
    def _load_from_store(self) -> None:
        """Load schedules from the persistent store into the in-memory heap.

        This method validates and recomputes `next_run_ts` when necessary and
        applies misfire behavior for overdue schedules.
        """
        logger.debug("Loading schedules from store")
        with self._lock:
            self._heap.clear()
            self._jobs_by_id.clear()
            for s in self.store.list_all():
                # skip disabled schedules
                if not s.enabled:
                    continue

                # Ensure next_run_ts exists
                try:
                    if s.next_run_ts is None:
                        s.next_run_ts = s.compute_next_run_ts()
                except Exception as e:
                    logger.error("Failed computing next_run_ts for %s: %s", s.id, e)
                    continue

                # Apply misfire policy if it's already in the past
                now = time.time()
                if s.next_run_ts and s.next_run_ts < now:
                    self._handle_misfire(s, now)

                self._push_schedule(s)
                self._jobs_by_id[s.id] = s
                self._running_counts.setdefault(s.id, 0)

            logger.info("Loaded %d schedules", len(self._jobs_by_id))

    # ---------------------------- public API -------------------------------
    def add_schedule(self, job: ScheduledJob) -> ScheduledJob:
        """
        Persist and register a new ScheduledJob.
        Returns the stored ScheduledJob (store may assign IDs/fields).
        """
        with self._lock:
            stored = self.store.add(job)
            # recompute next run to be safe
            stored.next_run_ts = stored.compute_next_run_ts()
            stored.touch_updated()
            self._jobs_by_id[stored.id] = stored
            self._push_schedule(stored)
            self._wakeup_event.set()
            logger.info("Added schedule %s -> next=%s", stored.id, stored.next_run_ts)
            return stored

    def update_schedule(self, job: ScheduledJob) -> None:
        """
        Update an existing schedule in the store and in-memory structures.
        """
        with self._lock:
            self.store.update(job)
            job.touch_updated()
            # replace in-memory
            self._jobs_by_id[job.id] = job
            # rebuild heap for simplicity
            self._rebuild_heap()
            self._wakeup_event.set()
            logger.info("Updated schedule %s", job.id)

    def remove_schedule(self, schedule_id: str) -> None:
        """
        Remove a schedule by ID from both store and in-memory structures.
        """
        with self._lock:
            self.store.remove(schedule_id)
            if schedule_id in self._jobs_by_id:
                del self._jobs_by_id[schedule_id]
            # rebuild heap
            self._rebuild_heap()
            self._wakeup_event.set()
            logger.info("Removed schedule %s", schedule_id)

    def list_schedules(self) -> List[ScheduledJob]:
        """Return a copy of all registered schedules."""
        with self._lock:
            return list(self._jobs_by_id.values())

    def enable_schedule(self, schedule_id: str) -> None:
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
        with self._lock:
            s = self.store.get(schedule_id)
            if not s:
                raise KeyError(schedule_id)
            s.enabled = False
            s.touch_updated()
            self.store.update(s)
            if schedule_id in self._jobs_by_id:
                del self._jobs_by_id[schedule_id]
            self._rebuild_heap()
            self._wakeup_event.set()

    def run_once_now(self, schedule_id: str) -> Optional[str]:
        """
        Force-run a schedule immediately (creates a Job). Returns the created
        Job id if successful, otherwise None.
        """
        with self._lock:
            s = self._jobs_by_id.get(schedule_id) or self.store.get(schedule_id)
            if not s:
                raise KeyError(schedule_id)
            job = self._dispatch_schedule(s)
            return getattr(job, "id", None)

    # ---------------------------- internal heap ---------------------------
    def _push_schedule(self, s: ScheduledJob) -> None:
        if s.next_run_ts is None:
            return
        heapq.heappush(self._heap, (float(s.next_run_ts), s.id))

    def _rebuild_heap(self) -> None:
        self._heap = []
        for s in self._jobs_by_id.values():
            if s.enabled and s.next_run_ts:
                heapq.heappush(self._heap, (float(s.next_run_ts), s.id))

    def _pop_due(self, until_ts: float) -> List[ScheduledJob]:
        due = []
        while self._heap and self._heap[0][0] <= until_ts:
            _, sid = heapq.heappop(self._heap)
            s = self._jobs_by_id.get(sid)
            if s and s.enabled:
                due.append(s)
        return due

    # ---------------------------- misfire handling ------------------------
    def _handle_misfire(self, s: ScheduledJob, now: float) -> None:
        """Apply misfire policy for a schedule whose next_run_ts is in the past."""
        logger.warning("Schedule %s missed (next_run=%s, now=%s) - policy=%s", s.id, s.next_run_ts, now, s.misfire_policy)
        if s.misfire_policy == "run_immediately":
            # leave next_run_ts as in the past; _run_loop will pick it up immediately
            return
        if s.misfire_policy == "skip":
            # compute next
            s.next_run_ts = s.compute_next_run_ts(from_ts=now)
            self.store.update(s)
            return
        if s.misfire_policy == "reschedule":
            # place next run at now
            s.next_run_ts = now
            self.store.update(s)
            return

    # ---------------------------- dispatch --------------------------------
    def _dispatch_schedule(self, s: ScheduledJob):
        """Create a Nuvom Job from the ScheduledJob by invoking the task's .delay().

        Returns the Job object or raises if the task cannot be resolved.
        """
        logger.debug("Dispatching schedule %s -> task %s", s.id, s.task_name)
        task = get_task(s.task_name)
        if not task:
            raise RuntimeError(f"Scheduled task not found in registry: {s.task_name}")

        # enforce concurrency limit
        rc = self._running_counts.get(s.id, 0)
        if s.concurrency_limit and rc >= s.concurrency_limit:
            logger.info("Schedule %s concurrency limit reached (%s)", s.id, s.concurrency_limit)
            return None

        # increment running counter
        self._running_counts[s.id] = rc + 1

        try:
            job = task.delay(*s.args, **s.kwargs)
            logger.info("Scheduled job %s created for schedule %s", getattr(job, "id", None), s.id)
            return job
        finally:
            # decrement running counter immediately after creation; actual runtime
            # will be enforced by JobRunner and workers. This counter is a best-effort
            # guard for quick throttle; a more accurate mechanism would hook into
            # job lifecycle events (on_start/on_complete).
            self._running_counts[s.id] = max(0, self._running_counts.get(s.id, 1) - 1)

    # ---------------------------- main loop -------------------------------
    def _run_loop(self) -> None:
        logger.info("Scheduler loop started")
        while not self._stop_event.is_set():
            with self._lock:
                if not self._heap:
                    # wait longer if nothing is scheduled
                    self._wakeup_event.clear()

                # compute next wake-up time
                if not self._heap:
                    timeout = self._tick
                else:
                    next_ts = self._heap[0][0]
                    now = time.time()
                    timeout = max(0.0, next_ts - now)

            # Wait until either the timeout elapses or a wakeup is signalled
            awakened = self._wakeup_event.wait(timeout=timeout)
            if self._stop_event.is_set():
                break
            # reset wakeup flag
            self._wakeup_event.clear()

            now = time.time()
            # pop and dispatch due schedules
            with self._lock:
                due = self._pop_due(until_ts=now + 1e-6)

            for s in due:
                try:
                    self._dispatch_schedule(s)
                except Exception as e:
                    logger.exception("Failed dispatching schedule %s: %s", s.id, e)

                # Post-dispatch: update next_run_ts for recurring schedules
                if s.schedule_type in ("interval", "cron"):
                    try:
                        s.next_run_ts = s.compute_next_run_ts(from_ts=time.time())
                        s.touch_updated()
                        self.store.update(s)
                    except Exception as e:
                        logger.exception("Failed computing/updating next_run_ts for %s: %s", s.id, e)
                    # reinsert
                    with self._lock:
                        self._push_schedule(s)
                else:
                    # one-off: disable or remove depending on persisted policy
                    s.enabled = False
                    s.touch_updated()
                    try:
                        self.store.update(s)
                    except Exception:
                        # best effort
                        logger.exception("Failed disabling one-off schedule %s", s.id)

        logger.info("Scheduler loop exiting")

