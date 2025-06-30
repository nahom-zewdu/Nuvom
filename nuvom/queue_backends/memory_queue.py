# nuvom/queue_backends/memory_queue.py

"""
MemoryJobQueue implements an in-memory FIFO job queue backend using Python's
thread-safe queue.Queue. It supports thread-safe enqueue, dequeue, batch pop,
and clearing of jobs. This backend is ephemeral and suitable for testing or
scenarios where persistence is not required.
"""

import queue
import threading

from nuvom.serialize import get_serializer
from nuvom.job import Job
from nuvom.log import logger
from nuvom.plugins.contracts import Plugin, API_VERSION

class MemoryJobQueue:
    """
    An in-memory job queue backed by queue.Queue with thread safety.

    Attributes:
        q (queue.Queue): Thread-safe queue instance storing jobs.
        lock (threading.Lock): Lock to synchronize batch operations.
        serializer: Serializer instance (currently unused but reserved).
    """
     # --- Plugin metadata --------------------------------------------------
    api_version = API_VERSION
    name        = "memory"
    provides    = ["queue_backend"]
    requires: list[str] = []

    # start/stop are no‑ops for this lightweight backend
    def start(self, settings: dict): ...
    def stop(self): ...

    def __init__(self, maxsize: int = 0):
        """
        Initialize the MemoryJobQueue.

        Args:
            maxsize (int): Maximum number of jobs allowed in the queue.
                           0 means infinite size.
        """
        self.q = queue.Queue(maxsize=maxsize)
        self.lock = threading.Lock()
        self.serializer = get_serializer()

    def enqueue(self, job: Job):
        """
        Add a job to the queue.

        Args:
            job (Job): Job instance to enqueue.
        """
        self.q.put(job)
        logger.debug(f"Enqueued job '{job.id}' in memory queue.")

    def dequeue(self, timeout: int = 1) -> Job | None:
        """
        Remove and return a job from the queue.

        Args:
            timeout (int): Time in seconds to wait for a job before returning None.

        Returns:
            Job or None: The dequeued job, or None if queue is empty.
        """
        try:
            job = self.q.get(timeout=timeout)
            logger.debug(f"Dequeued job '{job.id}' from memory queue.")
            return job
        except queue.Empty:
            logger.debug("Dequeue timed out - no jobs available in memory queue.")
            return None

    def pop_batch(self, batch_size: int = 1, timeout: int = 1) -> list[Job]:
        """
        Remove and return up to `batch_size` jobs from the queue.

        Args:
            batch_size (int): Maximum number of jobs to dequeue.
            timeout (int): Timeout in seconds to wait for each job.

        Returns:
            list[Job]: List of dequeued jobs, may be empty if no jobs available.
        """
        batch = []
        with self.lock:
            for _ in range(batch_size):
                try:
                    job = self.q.get(timeout=timeout)
                    batch.append(job)
                    logger.debug(f"Popped batch job '{job.id}' from memory queue.")
                except queue.Empty:
                    logger.debug("Batch pop timed out early - no more jobs available.")
                    break
        return batch

    def qsize(self) -> int:
        """
        Return the approximate number of jobs in the queue.

        Returns:
            int: Number of jobs currently in the queue.
        """
        size = self.q.qsize()
        logger.debug(f"Memory queue size: {size}.")
        return size

    def clear(self):
        """
        Remove all jobs from the queue.
        """
        with self.lock:
            cleared_count = 0
            while not self.q.empty():
                self.q.get()
                cleared_count += 1
            logger.info(f"Cleared {cleared_count} jobs from memory queue.")
