"""
Scheduler Worker
=================

A thin, production-ready wrapper that hosts the scheduler **dispatcher** in a
cooperative loop. It manages lifecycle (start/stop), background threading, and
integration with the rest of the Nuvom pipeline.

What this worker does
---------------------
- Periodically asks the scheduler backend for **due** schedule envelopes via the
  dispatcher, which then converts them into regular `Job`s and enqueues them to
  the **main task queue**.
- Runs safely alongside multiple replicas. The backend is responsible for
  concurrency guarantees (e.g., only returning `pending` items in `due()`).
- Provides a small API for embedding in apps/services or running as a
  standalone process.

Design choices
--------------
- Delegates *all* business logic to `nuvom.scheduler.dispatcher.Dispatcher`.
  This keeps the worker focused on lifecycle management and resilience.
- Uses a cooperative `stop_event` that allows graceful shutdown between polls.
- Exposes `start(background=True)`, `stop(timeout=None)`, and `run()` to fit
  CLI daemons as well as embedded usage in tests.

Usage example
-------------
>>> from nuvom.scheduler.worker import SchedulerWorker
>>> worker = SchedulerWorker(poll_interval=1.0, batch_size=100, jitter=0.2)
>>> worker.start(background=True)
... # later
>>> worker.stop()

This module does not import or reference queue/job internals directly; those
are handled by `dispatcher`.
"""

from __future__ import annotations

import threading
from typing import Optional

from nuvom.log import get_logger
from nuvom.scheduler.dispatcher import Dispatcher

logger = get_logger()


class SchedulerWorker:
    """
    Host the scheduler dispatcher in a managed loop.

    Parameters
    ----------
    poll_interval : float, optional
        Base sleep interval (seconds) when nothing is due. Default: 1.0.
    batch_size : int, optional
        Maximum number of due envelopes dispatched per iteration. Default: 100.
    jitter : float, optional
        Random additive seconds to the sleep duration (0..jitter) to avoid
        lock-step polling across replicas. Default: 0.0.
    name : str, optional
        Thread name when running in background. Default: "NuvomSchedulerWorker".

    Notes
    -----
    - `SchedulerWorker` is intentionally thin; it instantiates a
      `nuvom.scheduler.dispatcher.Dispatcher` and delegates to its
      `run_forever()` loop.
    - Multiple workers can run concurrently. Backends must ensure that `due()`
      returns only claimable/pending envelopes and that lifecycle methods are
      idempotent.
    """

    def __init__(
        self,
        *,
        poll_interval: float = 1.0,
        batch_size: int = 100,
        jitter: float = 0.0,
        name: str = "NuvomSchedulerWorker",
    ) -> None:
        self.poll_interval = float(poll_interval)
        self.batch_size = int(batch_size)
        self.jitter = float(jitter)
        self.name = name

        self._dispatcher = Dispatcher()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self, *, background: bool = True) -> None:
        """Start the worker loop.

        If *background* is True (default), the loop runs in a daemon thread and
        this call returns immediately. Otherwise, this call blocks and only
        returns when `stop()` is invoked (from another thread) or the loop
        exits.
        """
        if self.is_running:
            logger.debug("[scheduler.worker] Already running.")
            return

        self._stop_event.clear()

        if background:
            self._thread = threading.Thread(
                target=self.run,
                name=self.name,
                daemon=True,
            )
            self._thread.start()
            logger.info("[scheduler.worker] Started in background thread '%s'", self.name)
        else:
            logger.info("[scheduler.worker] Running in foreground (blocking)...")
            self.run()  # blocking

    def run(self) -> None:
        """Blocking loop that drives the dispatcher until `stop()` is called."""
        try:
            self._dispatcher.run_forever(
                poll_interval=self.poll_interval,
                batch_size=self.batch_size,
                jitter=self.jitter,
                stop_event=self._stop_event,
            )
        except Exception:  # pragma: no cover - defensive: keep worker alive in hosts
            logger.exception("[scheduler.worker] Dispatcher loop crashed unexpectedly.")
            raise

    def stop(self, timeout: Optional[float] = None) -> None:
        """Request a graceful shutdown and optionally join the worker thread.

        Parameters
        ----------
        timeout : float, optional
            Seconds to wait for the background thread to exit. Ignored if the
            worker is not running or is in foreground mode.
        """
        if not self.is_running:
            return

        logger.info("[scheduler.worker] Stop requested.")
        self._stop_event.set()

        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)
            logger.info("[scheduler.worker] Stopped.")
        self._thread = None

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    @property
    def is_running(self) -> bool:
        """Return True if the worker is currently running in a thread."""
        t = self._thread
        return bool(t and t.is_alive())

    def run_once(self) -> int:
        """Dispatch a single batch immediately (useful for tests)."""
        try:
            return self._dispatcher.run_once(batch_size=self.batch_size)
        except Exception:
            logger.exception("[scheduler.worker] run_once failed.")
            return 0


# ---------------------------------------------------------------------- #
# Module-level helpers
# ---------------------------------------------------------------------- #

def run_worker_forever(
    *, poll_interval: float = 1.0, batch_size: int = 100, jitter: float = 0.0
) -> None:
    """Convenience function to run a scheduler worker in the foreground."""
    SchedulerWorker(
        poll_interval=poll_interval, batch_size=batch_size, jitter=jitter
    ).start(background=False)
