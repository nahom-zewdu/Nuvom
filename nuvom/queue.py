# nuvom/queue.py

"""
Queue management interface for jobs.

Delegates all persistence to a *configurable* backend class, which is resolved
via Nuvom’s plugin registry (`nuvom.plugins.registry`).  This allows third‑party
packages to add custom queue implementations without touching core code.
"""

from __future__ import annotations

from typing import List, Optional

from nuvom.config import get_settings
from nuvom.job import Job
from nuvom.plugins.registry import get_queue_backend_cls

# Cached singleton instance
_global_queue = None


# --------------------------------------------------------------------------- #
#  Backend resolution
# --------------------------------------------------------------------------- #
def get_queue_backend():
    """
    Return the active queue backend (singleton).

    • Uses the short name in ``NUVOM_QUEUE_BACKEND``  
    • Looks up the concrete class from the plugin registry  
    • Instantiates it lazily on first call
    """
    global _global_queue
    if _global_queue is not None:
        return _global_queue

    settings = get_settings()
    backend_name = settings.queue_backend.lower()
    backend_cls = get_queue_backend_cls(backend_name)

    if backend_cls is None:
        raise ValueError(f"Unsupported or unregistered queue backend: {backend_name}")

    _global_queue = backend_cls()
    return _global_queue


# --------------------------------------------------------------------------- #
#  Thin convenience wrappers
# --------------------------------------------------------------------------- #
def enqueue(job: Job) -> None:
    """Add a job to the active queue backend."""
    get_queue_backend().enqueue(job)


def dequeue(timeout: int = 1) -> Optional[Job]:
    """Remove & return a job, blocking up to ``timeout`` seconds."""
    return get_queue_backend().dequeue(timeout)


def pop_batch(batch_size: int = 1, timeout: int = 1) -> List[Job]:
    """Remove & return up to ``batch_size`` jobs."""
    return get_queue_backend().pop_batch(batch_size=batch_size, timeout=timeout)


def qsize() -> int:
    """Return the current queue length."""
    return get_queue_backend().qsize()


def clear() -> int:
    """
    Remove **all** jobs from the backend.

    Returns
    -------
    int
        Number of jobs removed.
    """
    return get_queue_backend().clear()
