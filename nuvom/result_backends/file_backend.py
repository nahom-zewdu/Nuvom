# nuvom/result_backends/file_backend.py

"""
FileResultBackend provides a persistent file-based implementation of the result backend.

Stores job results and error metadata in serialized files using a dedicated directory.
Persists all job metadata to `.meta` files for inspection and introspection support.
"""

import os
import traceback
from typing import Optional, Any

from nuvom.result_backends.base import BaseResultBackend
from nuvom.serialize import serialize, deserialize
from nuvom.plugins.contracts import Plugin, API_VERSION


class FileResultBackend(BaseResultBackend):
    """
    A file-based result backend that persists job outcomes to disk.

    Stores structured metadata (status, args, tracebacks, timestamps, etc.)
    in `.meta` files for each job. Falls back to legacy `.out` and `.err`.

    Attributes:
        result_dir (str): Directory for all job result files.
    """

    # --- Plugin metadata --------------------------------------------------
    api_version = API_VERSION
    name        = "file"
    provides    = ["result_backend"]
    requires: list[str] = []
    
    def __init__(self):
        self.result_dir = "job_results"
        os.makedirs(self.result_dir, exist_ok=True)

    # start/stop are no‑ops for this lightweight backend
    def start(self, settings: dict): ...
    def stop(self): ...

    def _path(self, job_id, ext: str = "meta") -> str:
        """Construct the full file path for a job's metadata file."""
        return os.path.join(self.result_dir, f"{job_id}.{ext}")

    def set_result(
        self,
        job_id: str,
        func_name:str,
        result: Any,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ):
        """Store full result metadata to a `.meta` file."""
        data = {
            "job_id": job_id,
            "func_name":func_name,
            "status": "SUCCESS",
            "result": result,
            "args": args or [],
            "kwargs": kwargs or {},
            "retries_left": retries_left,
            "attempts": attempts,
            "created_at": created_at,
            "completed_at": completed_at,
        }
        with open(self._path(job_id), "wb") as f:
            f.write(serialize(data))

    def get_result(self, job_id: str) -> Optional[Any]:
        """Load only the result value from metadata or fallback `.out`."""
        meta_path = self._path(job_id)
        if os.path.exists(meta_path):
            with open(meta_path, "rb") as f:
                return deserialize(f.read()).get("result")

        # fallback: legacy file
        out_path = self._path(job_id, "out")
        if os.path.exists(out_path):
            with open(out_path, "rb") as f:
                return deserialize(f.read())
        return None

    def set_error(
        self,
        job_id: str,
        func_name:str,
        error: Exception,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ):
        """Store full error metadata to a `.meta` file."""
        tb_str = traceback.format_exc()
        data = {
            "job_id": job_id,
            "func_name":func_name,
            "status": "FAILED",
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": tb_str,
            },
            "args": args or [],
            "kwargs": kwargs or {},
            "retries_left": retries_left,
            "attempts": attempts,
            "created_at": created_at,
            "completed_at": completed_at,
        }

        with open(self._path(job_id), "wb") as f:
            f.write(serialize(data))

    def get_error(self, job_id: str) -> Optional[str]:
        """Retrieve the error message from metadata or fallback `.err` file."""
        meta_path = self._path(job_id)
        if os.path.exists(meta_path):
            with open(meta_path, "rb") as f:
                data = deserialize(f.read())
                return data.get("error", {}).get("message")

        err_path = self._path(job_id, "err")
        if os.path.exists(err_path):
            with open(err_path, "r") as f:
                return f.read()
        return None

    def get_full(self, job_id: str) -> Optional[dict]:
        """Return full job state metadata from `.meta` file if available."""
        meta_path = self._path(job_id)
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, "rb") as f:
            return deserialize(f.read())

    def list_jobs(self) -> list[dict]:
        """
        Return full metadata for all jobs in the result directory.

        Returns:
            List of job metadata dicts (as returned by get_full()).
        """
        jobs = []
        for file in os.listdir(self.result_dir):
            if file.endswith(".meta"):
                job_id = file.rsplit(".", 1)[0]
                full = self.get_full(job_id)
                if full:
                    jobs.append(full)
        return jobs