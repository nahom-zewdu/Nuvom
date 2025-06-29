# nuvom/queue.py

"""
Queue management interface for jobs.
Uses a configurable backend to manage job lifecycles.
"""

"""
Queue management interface for jobs, now plugin‑aware.
"""

from typing import List, Optional

from nuvom.config import get_settings
from nuvom.plugins.registry import get_queue_backend_cls, register_queue_backend
from nuvom.queue_backends.file_queue import FileJobQueue
from nuvom.queue_backends.memory_queue import MemoryJobQueue
from nuvom.job import Job
from nuvom.log import logger

# --------------------------------------------------------------------------- #
#  Register built‑in backends (redundant but explicit for clarity)
# --------------------------------------------------------------------------- #
register_queue_backend("file", FileJobQueue, override=True)
register_queue_backend("memory", MemoryJobQueue, override=True)

# --------------------------------------------------------------------------- #
#  Global singleton
# --------------------------------------------------------------------------- #
_global_queue = None


def _instantiate_backend(name: str):
    """
    Resolve `name` via plugin registry, falling back to ValueError if missing.
    """
    cls = get_queue_backend_cls(name)
    if cls is None:
        raise ValueError(f"Unsupported queue backend: {name}")
    logger.debug("[Queue] Using backend '%s' (%s)", name, cls.__name__)
    return cls()


def get_queue_backend():
    """
    Return a singleton instance of the configured queue backend.
    """
    global _global_queue
    if _global_queue is not None:
        return _global_queue

    backend_name = get_settings().queue_backend.lower()
    _global_queue = _instantiate_backend(backend_name)
    return _global_queue


def enqueue(job: Job):
    """
    Add a job to the queue.
    """
    get_queue_backend().enqueue(job)


def dequeue(timeout: int = 1) -> Optional[Job]:
    """
    Remove and return a job from the queue, blocking up to `timeout` seconds.
    """
    return get_queue_backend().dequeue(timeout)


def pop_batch(batch_size: int = 1, timeout: int = 1) -> List[Job]:
    """
    Remove and return up to `batch_size` jobs from the queue.
    """
    return get_queue_backend().pop_batch(batch_size=batch_size, timeout=timeout)


def qsize() -> int:
    """
    Return the number of jobs currently in the queue.
    """
    return get_queue_backend().qsize()


def clear() -> int:
    """
    Clear all jobs from the queue.
    Returns the number of jobs cleared.
    """
    return get_queue_backend().clear()
