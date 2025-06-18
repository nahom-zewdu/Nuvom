# nuvom/queue_backends/base.py

"""
Abstract base class defining the interface for job queue backends.

This class enforces implementation of core queue operations:
- enqueue: add a job to the queue.
- dequeue: remove and return a job with optional timeout.
- pop_batch: remove and return multiple jobs at once.
- qsize: query the current number of jobs in the queue.
- clear: remove all jobs from the queue.

Concrete backend implementations must override all abstract methods.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from nuvom.job import Job


class BaseJobQueue(ABC):
    """
    Interface for job queue backends.

    All methods are abstract and must be implemented by subclasses to
    provide a consistent job queue API.
    """

    @abstractmethod
    def enqueue(self, job: Job):
        """
        Add a job to the queue.

        Args:
            job (Job): The job instance to enqueue.
        """
        pass

    @abstractmethod
    def dequeue(self, timeout: int = 1) -> Optional[Job]:
        """
        Remove and return a job from the queue.

        Args:
            timeout (int): Time in seconds to wait for a job if queue is empty.

        Returns:
            Optional[Job]: The dequeued job, or None if no job is available
                           within the timeout.
        """
        pass

    @abstractmethod
    def pop_batch(self, batch_size: int = 1, timeout: int = 1) -> List[Job]:
        """
        Remove and return up to batch_size jobs from the queue.

        Args:
            batch_size (int): Maximum number of jobs to dequeue.
            timeout (int): Time in seconds to wait for each job.

        Returns:
            List[Job]: List of dequeued jobs, which may be fewer than batch_size
                       if not enough jobs are available.
        """
        pass

    @abstractmethod
    def qsize(self) -> int:
        """
        Return the approximate number of jobs currently in the queue.

        Returns:
            int: Number of jobs in the queue.
        """
        pass

    @abstractmethod
    def clear(self):
        """
        Remove all jobs from the queue.
        """
        pass
