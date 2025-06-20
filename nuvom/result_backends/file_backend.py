# nuvom/result_backends/file_backend.py

"""
FileResultBackend provides a simple file-based implementation of the result backend.

Results are serialized and stored in a dedicated directory, with each job's result
and error saved in separate files. Supports persistence across restarts.
"""

import os

from nuvom.result_backends.base import BaseResultBackend
from nuvom.serialize import serialize, deserialize


class FileResultBackend(BaseResultBackend):
    """
    A file-based result backend for persisting job results and errors.

    Attributes:
        result_dir (str): Directory where result and error files are stored.

    Methods:
        set_result(job_id, result): Store a job's result to disk.
        get_result(job_id): Load a job's result from disk.
        set_error(job_id, error): Store a job's error to disk.
        get_error(job_id): Load a job's error message from disk.
    """

    def __init__(self):
        """
        Initialize the result backend and create the results directory if needed.
        """
        self.result_dir = "job_results"
        os.makedirs(self.result_dir, exist_ok=True)

    def _path(self, job_id):
        """Construct the file path for storing the job result."""
        return os.path.join(self.result_dir, f"{job_id}.out")

    def _err_path(self, job_id):
        """Construct the file path for storing the job error message."""
        return os.path.join(self.result_dir, f"{job_id}.err")

    def set_result(self, job_id, result):
        """
        Store the serialized result of a job in a file.

        Args:
            job_id (str): Unique job identifier.
            result (Any): Result object to serialize and store.
        """
        os.makedirs(self.result_dir, exist_ok=True)
        with open(self._path(job_id), "wb") as f:
            f.write(serialize(result))

    def get_result(self, job_id):
        """
        Retrieve and deserialize the result for a job.

        Args:
            job_id (str): Unique job identifier.

        Returns:
            Any: The deserialized result, or None if not found.
        """
        path = self._path(job_id)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return deserialize(f.read())

    def set_error(self, job_id, error):
        """
        Store the error message of a failed job in a file.

        Args:
            job_id (str): Unique job identifier.
            error (str): Error message to store.
        """
        os.makedirs(self.result_dir, exist_ok=True)
        with open(self._err_path(job_id), "w") as f:
            f.write(str(error))

    def get_error(self, job_id):
        """
        Retrieve the stored error message for a failed job.

        Args:
            job_id (str): Unique job identifier.

        Returns:
            str | None: The error message, or None if not found.
        """
        path = self._err_path(job_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return f.read()
