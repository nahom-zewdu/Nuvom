# nuvom/result_backends/base.py

"""
Abstract base class for result backends that store job results and errors.

Defines the required interface for any result backend, including methods
to store and retrieve both successful results and error messages.
"""

from abc import ABC, abstractmethod


class BaseResultBackend(ABC):
    """
    Interface for result backends used to persist job results and errors.

    Methods:
        set_result(job_id, result): Persist the result of a completed job.
        get_result(job_id): Retrieve the result for a given job ID.
        set_error(job_id, error): Persist an error message for a failed job.
        get_error(job_id): Retrieve the error message for a given job ID.
    """

    @abstractmethod
    def set_result(self, job_id: str, result: object):
        """
        Store the result of a completed job.

        Args:
            job_id: Unique identifier for the job.
            result: The result object to store.
        """
        pass

    @abstractmethod
    def get_result(self, job_id: str) -> object:
        """
        Retrieve the result for a completed job.

        Args:
            job_id: Unique identifier for the job.

        Returns:
            The stored result object.
        """
        pass

    @abstractmethod
    def set_error(self, job_id: str, error: str):
        """
        Store an error message for a failed job.

        Args:
            job_id: Unique identifier for the job.
            error: Error message to store.
        """
        pass

    @abstractmethod
    def get_error(self, job_id: str) -> str:
        """
        Retrieve the error message for a failed job.

        Args:
            job_id: Unique identifier for the job.

        Returns:
            The stored error message.
        """
        pass
