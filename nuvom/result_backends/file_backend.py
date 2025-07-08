# nuvom/result_backends/file_backend.py
"""
Persistent, file‑based result backend.

Improvements
------------
• Atomic write – temp file + os.replace() to avoid corrupt/partial files
• Accurate traceback capture for passed‑in Exception
• Re‑use helper _write() to DRY set_result / set_error
"""

from __future__ import annotations

import os
import traceback
from tempfile import NamedTemporaryFile
from typing import Any, Optional

from nuvom.result_backends.base import BaseResultBackend
from nuvom.serialize import deserialize, serialize
from nuvom.plugins.contracts import API_VERSION, Plugin


class FileResultBackend(BaseResultBackend):
    # ---- Plugin metadata --------------------------------------------- #
    api_version = API_VERSION
    name = "file"
    provides = ["result_backend"]
    requires: list[str] = []

    # ------------------------------------------------------------------ #
    def __init__(self, result_dir: str = "job_results") -> None:
        self.result_dir = result_dir
        os.makedirs(self.result_dir, exist_ok=True)

    # start/stop are no‑ops for this lightweight backend
    def start(self, settings: dict): ...
    def stop(self): ...

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _path(self, job_id: str, ext: str = "meta") -> str:
        return os.path.join(self.result_dir, f"{job_id}.{ext}")

    def _write_atomic(self, path: str, data: bytes) -> None:
        """Write file atomically to prevent partial writes under concurrency."""
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "wb") as tmp:
            tmp.write(data)
        os.replace(tmp_path, path)

    # ------------------------------------------------------------------ #
    # BaseResultBackend implementation
    # ------------------------------------------------------------------ #
    def set_result(
        self,
        job_id: str,
        func_name: str,
        result: Any,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ) -> None:
        meta = {
            "job_id": job_id,
            "func_name": func_name,
            "status": "SUCCESS",
            "result": result,
            "args": args or [],
            "kwargs": kwargs or {},
            "retries_left": retries_left,
            "attempts": attempts,
            "created_at": created_at,
            "completed_at": completed_at,
        }
        self._write_atomic(self._path(job_id), serialize(meta))

    def get_result(self, job_id: str) -> Optional[Any]:
        meta_path = self._path(job_id)
        if os.path.exists(meta_path):
            with open(meta_path, "rb") as f:
                return deserialize(f.read()).get("result")

        legacy = self._path(job_id, "out")
        if os.path.exists(legacy):
            with open(legacy, "rb") as f:
                return deserialize(f.read())
        return None

    def set_error(
        self,
        job_id: str,
        func_name: str,
        error: Exception,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ) -> None:
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        meta = {
            "job_id": job_id,
            "func_name": func_name,
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
        self._write_atomic(self._path(job_id), serialize(meta))

    def get_error(self, job_id: str) -> Optional[str]:
        meta_path = self._path(job_id)
        if os.path.exists(meta_path):
            with open(meta_path, "rb") as f:
                data = deserialize(f.read())
            return data.get("error", {}).get("message")

        legacy = self._path(job_id, "err")
        if os.path.exists(legacy):
            with open(legacy, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def get_full(self, job_id: str) -> Optional[dict]:
        meta_path = self._path(job_id)
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, "rb") as f:
            return deserialize(f.read())

    def list_jobs(self) -> list[dict]:
        jobs = []
        for file in os.listdir(self.result_dir):
            if file.endswith(".meta"):
                job_id = file[:-5]  # strip ".meta"
                if full := self.get_full(job_id):
                    jobs.append(full)
        return jobs
