# nuvom/backends/memory_backend.py

"""
MemoryResultBackend provides an in-memory implementation of the result backend.

Useful for testing and non-persistent environments. Stores serialized job results
and error messages in dictionaries. All data is lost on process termination.
"""

from nuvom.serialize import serialize, deserialize
from nuvom.result_backends.base import BaseResultBackend


class MemoryResultBackend(BaseResultBackend):
    """
    In-memory result backend for storing job results and errors temporarily.

    Attributes:
        _results (dict): Maps job_id to serialized result.
        _errors (dict): Maps job_id to error message strings.

    Methods:
        set_result(job_id, result): Serialize and store the job result.
        get_result(job_id): Deserialize and return stored result.
        set_error(job_id, error): Store job error as string.
        get_error(job_id): Return stored error string.
    """

    def __init__(self):
        """Initialize in-memory result and error stores."""
        self._results = {}
        self._errors = {}

    def set_result(self, job_id, result):
        """
        Store a job's result in serialized form.

        Args:
            job_id (str): Unique identifier for the job.
            result (Any): The result object to store.
        """
        self._results[job_id] = serialize(result)

    def get_result(self, job_id):
        """
        Retrieve and deserialize a stored job result.

        Args:
            job_id (str): Unique identifier for the job.

        Returns:
            Any or None: The deserialized result, or None if not found.
        """
        raw = self._results.get(job_id)
        return deserialize(raw) if raw else None

    def set_error(self, job_id, error):
        """
        Store an error message for a failed job.

        Args:
            job_id (str): Unique identifier for the job.
            error (str): The error message.
        """
        self._errors[job_id] = str(error)

    def get_error(self, job_id) -> str:
        """
        Retrieve the error message for a failed job.

        Args:
            job_id (str): Unique identifier for the job.

        Returns:
            str or None: The stored error message, or None if not found.
        """
        return self._errors.get(job_id)
