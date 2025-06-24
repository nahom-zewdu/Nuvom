# nuvom/result_backends/base.py

"""
Abstract base class for result backends that store job results and errors.

Defines the required interface for any result backend, including methods
to store and retrieve both successful results and error messages.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseResultBackend(ABC):
    """
    Interface for result backends used to persist job results and errors.

    Methods:
        set_result: Persist result along with job metadata.
        get_result: Retrieve deserialized result.
        set_error: Persist error along with job metadata and traceback.
        get_error: Retrieve error message.
        get_full: Retrieve all metadata associated with a job.
    """

    @abstractmethod
    def set_result(
        self,
        job_id: str,
        result: Any,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ):
        """
        Store the result of a completed job with full metadata.

        Args:
            job_id: Unique identifier for the job.
            result: The result object to store.
            args: The positional arguments used by the job.
            kwargs: The keyword arguments used by the job.
            retries_left: Number of retries remaining.
            attempts: Number of attempts made.
            created_at: Timestamp when job was created.
            completed_at: Timestamp when job finished.
        """
        pass

    @abstractmethod
    def get_result(self, job_id: str) -> Any:
        """
        Retrieve only the result for a given job ID.

        Args:
            job_id: Unique identifier for the job.

        Returns:
            The stored result object or None.
        """
        pass

    @abstractmethod
    def set_error(
        self,
        job_id: str,
        error: Exception,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ):
        """
        Store an error for a failed job with full metadata and traceback.

        Args:
            job_id: Unique identifier for the job.
            error: The error/exception to store.
            args: Arguments used in the job.
            kwargs: Keyword arguments used in the job.
            retries_left: Number of retries remaining.
            attempts: Number of attempts made.
            created_at: Timestamp when job was created.
            completed_at: Timestamp when job failed.
        """
        pass

    @abstractmethod
    def get_error(self, job_id: str) -> Optional[str]:
        """
        Retrieve only the error message or traceback string.

        Args:
            job_id: Unique identifier for the job.

        Returns:
            Error string or None.
        """
        pass

    @abstractmethod
    def get_full(self, job_id: str) -> Optional[dict]:
        """
        Return a full dictionary of job metadata, whether success or failure.

        Args:
            job_id: Unique identifier for the job.

        Returns:
            Dict containing status, args, result/error, timestamps, etc.
        """
        pass
