# Maintains the job buffer (FIFO or priority)
# Supports optional batch pulls
# Backpressure handling if needed

# nuvom/job_queue.py
from typing import List, Optional

from nuvom.config import get_settings
from nuvom.queue_backends.file_queue import FileJobQueue
from nuvom.queue_backends.memory_queue import MemoryJobQueue
from nuvom.job import Job

_global_queue = None

def get_queue_backend():
    global _global_queue
    if _global_queue is not None:
        return _global_queue

    backend_name = get_settings().queue_backend.lower()
    
    if backend_name == "file":
        _global_queue = FileJobQueue()
    elif backend_name == "memory":
        _global_queue = MemoryJobQueue()
    else:
        raise ValueError(f"Unsupported queue backend: {backend_name}")
    
    return _global_queue

def enqueue(job: Job):
    """Add a job to the queue."""
    get_queue_backend().enqueue(job)

def dequeue(timeout: int = 1) -> Optional[Job]:
    """Remove and return a job from the queue."""
    return get_queue_backend().dequeue(timeout)

def pop_batch(batch_size: int = 1, timeout: int = 1) -> List[Job]:
    """Remove and return up to batch_size jobs."""
    return get_queue_backend().pop_batch(batch_size=batch_size, timeout=timeout)

def qsize() -> int:
    """Return the number of jobs in the queue."""
    return get_queue_backend().qsize()

def clear() -> int:
    """Clear out the queue."""
    return get_queue_backend().clear()
