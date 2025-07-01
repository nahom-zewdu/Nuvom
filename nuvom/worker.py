# nuvom/worker.py

"""
nuvom.worker
~~~~~~~~~~~~
Thread-based worker pool with *graceful* lifecycle management.

Key upgrades (v0.9):
    • SIGINT / SIGTERM are trapped and routed to a global ``_shutdown_event``.
    • Workers stop polling once the event is set *and* their personal queue is empty.
    • Dispatcher stops once the event is set and all jobs are assigned.
    • Clean join() logic prints progress and guarantees no thread leak.
"""

from __future__ import annotations

import queue
import signal
import threading
import time
from typing import List

from nuvom.config import get_settings
from nuvom.execution.job_runner import JobRunner
from nuvom.log import logger
from nuvom.queue import get_queue_backend
from nuvom.registry.auto_register import auto_register_from_manifest
from nuvom.plugins.loader import LOADED_PLUGINS

# ------------------------------------------------------------------------- #
_shutdown_event = threading.Event()          # Global stop-flag for all threads
# ------------------------------------------------------------------------- #


class WorkerThread(threading.Thread):
    """
    Dedicated worker that pulls jobs from an *in-memory* queue injected by the
    dispatcher. It finishes outstanding work before exiting.

    Attributes
    ----------
    worker_id : int
        Logical identifier used for logs.
    job_timeout : int
        Default timeout passed to JobRunner.
    """

    def __init__(self, worker_id: int, job_timeout: int) -> None:
        super().__init__(daemon=True, name=f"Worker-{worker_id}")
        self.worker_id = worker_id
        self.job_timeout = job_timeout
        self._job_queue: queue.Queue = queue.Queue()
        self._in_flight = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #
    def submit(self, job) -> None:
        """Push a job into this worker’s personal queue."""
        self._job_queue.put(job)

    def load(self) -> int:
        """Current number of in-flight jobs."""
        with self._lock:
            return self._in_flight

    # ------------------------------------------------------------------ #
    # Thread body
    # ------------------------------------------------------------------ #
    def run(self) -> None:  # noqa: D401 – documented above
        logger.info("[Worker-%s] Online.", self.worker_id)

        while True:
            # Break when shutdown is requested AND queue is empty
            if _shutdown_event.is_set() and self._job_queue.empty():
                logger.info("[Worker-%s] Drained – shutting down.", self.worker_id)
                break

            try:
                job = self._job_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            with self._lock:
                self._in_flight += 1

            logger.debug("[Worker-%s] Executing job %s (%s)", self.worker_id, job.id, job.func_name)

            JobRunner(job, self.worker_id, self.job_timeout).run()

            logger.info("[Worker-%s] Completed %s → %s", self.worker_id, job.func_name, job.result)

            with self._lock:
                self._in_flight -= 1


class DispatcherThread(threading.Thread):
    """
    Dispatcher polls the *shared queue backend* and assigns jobs to the
    least-loaded worker. It respects *retry_delay* and halts on shutdown.
    """

    def __init__(self, workers: List[WorkerThread], batch_size: int, job_timeout: int) -> None:
        super().__init__(daemon=True, name="Dispatcher")
        self.workers = workers
        self.batch_size = batch_size
        self.job_timeout = job_timeout
        self.queue = get_queue_backend()

    def run(self) -> None:  # noqa: D401 – documented above
        logger.info("[Dispatcher] Started.")

        while not _shutdown_event.is_set():
            jobs = self.queue.pop_batch(self.batch_size, timeout=1)
            if not jobs:
                continue

            for job in jobs:
                # Retry-delay handling
                if getattr(job, "next_retry_at", 0) and (job.next_retry_at or 0) > time.time():
                    self.queue.enqueue(job)
                    continue

                target = min(self.workers, key=lambda w: w.load())
                target.submit(job)
                logger.debug("[Dispatcher] Job %s → Worker-%s", job.id, target.worker_id)

        logger.info("[Dispatcher] Shutdown signal received – exiting.")


# ------------------------------------------------------------------------- #
# Graceful Pool Entrypoint
# ------------------------------------------------------------------------- #
def _install_signal_handlers() -> None:
    """Map SIGINT/SIGTERM to the global _shutdown_event."""

    def _handler(signum, _frame):  # noqa: D401 – small internal func
        logger.warning("[Signal] %s received – initiating graceful shutdown.", signal.Signals(signum).name)
        _shutdown_event.set()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def start_worker_pool() -> None:
    """
    Bootstrap the worker pool, run until Ctrl-C / SIGTERM, then
    drain gracefully and exit.
    """
    auto_register_from_manifest()
    _install_signal_handlers()

    cfg = get_settings()
    workers: list[WorkerThread] = [
        WorkerThread(i, job_timeout=cfg.job_timeout_secs) for i in range(cfg.max_workers)
    ]
    for w in workers:
        w.start()

    dispatcher = DispatcherThread(workers, batch_size=cfg.batch_size, job_timeout=cfg.job_timeout_secs)
    dispatcher.start()

    try:
        while dispatcher.is_alive():
            dispatcher.join(timeout=0.5)
    finally:
        # Make sure global flag is set (covers KeyboardInterrupt path)
        _shutdown_event.set()
        logger.info("[Pool] Awaiting %d worker threads…", len(workers))

        for w in workers:
            w.join()

        logger.info("[Pool] All workers stopped cleanly.")

        # ------------------------------------------------------------------------- #
        # Stop Plugins (if any)
        # ------------------------------------------------------------------------- #
        for plugin in LOADED_PLUGINS:
            try:
                logger.info("[Plugin] Stopping %s (%s)...", plugin.name, plugin.__class__.__name__)
                plugin.stop()
            except Exception as e:
                logger.exception("[Plugin] %s.stop() failed – %s", plugin.name, e)
