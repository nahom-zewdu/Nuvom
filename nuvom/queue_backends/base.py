# nuvom/queue_backends/base.py

"""
Abstract base class defining the interface for job queue backends.
Specifies required queue operations like enqueue, dequeue, batch pop,
size query, and clear, to be implemented by concrete backends.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from nuvom.job import Job

class BaseJobQueue(ABC):
    @abstractmethod
    def enqueue(self, job: Job):
        """Add a job to the queue."""
        pass

    @abstractmethod
    def dequeue(self, timeout: int = 1) -> Optional[Job]:
        """Remove and return a job from the queue."""
        pass

    @abstractmethod
    def pop_batch(self, batch_size: int = 1, timeout: int = 1) -> List[Job]:
        """Remove and return up to batch_size jobs."""
        pass

    @abstractmethod
    def qsize(self) -> int:
        """Return the number of jobs in the queue."""
        pass
    
    @abstractmethod
    def clear(self):
        """Clear all jobs from the queue."""
        pass
