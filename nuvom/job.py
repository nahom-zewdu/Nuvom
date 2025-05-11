# Encapsulates task call: func, args, metadata
# Tracks status: PENDING, RUNNING, SUCCESS, FAILURE
# Optional: exposes .get(timeout=5) with blocking

# nuvom/job.py

import uuid
import time
from enum import Enum

from nuvom.result_store import get_backend

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job:
    def __init__(self, func_name, args=None, kwargs=None, retries=0, store_result=True):
        self.id = str(uuid.uuid4())
        self.func_name = func_name  # name in task registry
        self.store_result = store_result
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.status = JobStatus.PENDING
        self.created_at = time.time()
        self.retries_left = retries
        self.max_retries = retries
        self.result = None
        self.error = None

    def to_dict(self):
        return {
            "id": self.id,
            "func_name": self.func_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "store_result": self.store_result,
            "status": self.status,
            "created_at": self.created_at,
            "retries_left": self.retries_left,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error,
        }
        
    @classmethod
    def from_dict(cls, data):
        print("2222222", data, "222222222222")
        job = cls(
            func_name=data["func_name"],
            args=tuple(data.get("args")),
            kwargs=data.get("kwargs"),
            retries=data.get("max_retries", 0),
            store_result=data.get("store_result", True),
        )
        print("333333333", job, "33333333333333333")
        # Override attributes that aren't part of __init__
        job.id = data.get("id")
        job.status = data.get("status", JobStatus.PENDING)
        job.created_at = data.get("created_at", time.time())
        job.retries_left = data.get("retries_left", job.max_retries)
        job.result = data.get("result")
        job.error = data.get("error")
        print("444444444444", job, "444444444444444")
        return job
    
    def run(self):
        from nuvom.task import get_task
        
        self.retries_left -= 1
        task = get_task(self.func_name)
        if not task:
            raise ValueError(f"Task '{self.func_name}' not found.")
        return task(*self.args, **self.kwargs)

    def get(self, timeout=None, interval=0.5):
        """
        Polls for result. Blocks until result is available or timeout is hit.
        """
        if not self.store_result:
            return
        
        backend = get_backend()
        start = time.time()

        while True:
            result = backend.get_result(self.id)
            if result is not None:
                return self.to_dict()

            error = backend.get_error(self.id)
            if error is not None:
                raise RuntimeError(f"Job failed: {error}")

            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError("Job result not ready within timeout")

            time.sleep(interval)

    def mark_running(self):
        self.status = JobStatus.RUNNING

    def mark_success(self, result):
        self.status = JobStatus.SUCCESS
        self.result = result

    def mark_failed(self, error):
        self.status = JobStatus.FAILED
        self.error = str(error)
        
    def can_retry(self):
        return self.retries_left > 0
