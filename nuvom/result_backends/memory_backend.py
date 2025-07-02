# nuvom/result_backends/memory_backend.py

"""
MemoryResultBackend provides an in-memory implementation of the result backend.

Useful for testing and non-persistent environments. Stores full job result
metadata in-memory, including status, return value, error details, and lifecycle info.
"""

import traceback
import time
from typing import List, Dict

from nuvom.serialize import serialize, deserialize
from nuvom.result_backends.base import BaseResultBackend
from nuvom.plugins.contracts import Plugin, API_VERSION

class MemoryResultBackend(BaseResultBackend):
    """
    In-memory result backend storing detailed job result metadata.
    Suitable for testing and non-persistent workflows.

    Each job record includes:
        - status: "SUCCESS" | "FAILED"
        - result: serialized return value
        - error: type, message, traceback (on failure)
        - args, kwargs: job input
        - retries_left, attempts
        - created_at, completed_at: timestamps
    """

    def __init__(self):
        self._store = {}

     # --- Plugin metadata --------------------------------------------------
    api_version = API_VERSION
    name        = "memory"
    provides    = ["queue_backend"]
    requires: list[str] = []

    # start/stop are no‑ops for this lightweight backend
    def start(self, settings: dict): ...
    def stop(self): ...

    def set_result(self, job_id, func_name, result, *, args=None, kwargs=None, retries_left=None, attempts=None, created_at=None, completed_at=None):
        """
        Store the result of a successful job along with metadata.
        """
        self._store[job_id] = {
            "job_id": job_id,
            "func_name": func_name,
            "status": "SUCCESS",
            "result": serialize(result),
            "error": None,
            "args": args or [],
            "kwargs": kwargs or {},
            "retries_left": retries_left,
            "attempts": attempts,
            "created_at": created_at or time.time(),
            "completed_at": completed_at
        }

    def get_result(self, job_id):
        """
        Return the deserialized result value if available.
        """
        entry = self._store.get(job_id)
        if entry and entry["status"] == "SUCCESS":
            return deserialize(entry["result"])
        return None

    def set_error(self, job_id, func_name, error, *, args=None, kwargs=None, retries_left=None, attempts=None, created_at=None, completed_at=None):
        """
        Store a failed job's error with structured traceback and metadata.
        """
        self._store[job_id] = {
            "job_id": job_id,
            "func_name":func_name,
            "status": "FAILED",
            "result": None,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            },
            "args": args or [],
            "kwargs": kwargs or {},
            "retries_left": retries_left,
            "attempts": attempts,
            "created_at": created_at or time.time(),
            "completed_at": completed_at,
        }

    def get_error(self, job_id):
        """
        Return the error message of a failed job, if present.
        """
        entry = self._store.get(job_id)
        if entry and entry["status"] == "FAILED":
            return entry["error"]
        return None

    def get_full(self, job_id):
        """
        Return the full metadata dict for a job.
        Used by `nuvom inspect`.
        """
        return self._store.get(job_id)

    def list_jobs(self) -> List[Dict]:
        """
        Return all job metadata stored in memory.

        Returns:
            List[Dict]: All job records.
        """
        return list(self._store.values())