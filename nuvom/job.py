# Encapsulates task call: func, args, metadata
# Tracks status: PENDING, RUNNING, SUCCESS, FAILURE
# Optional: exposes .get(timeout=5) with blocking

# nuvom/job.py

import uuid
import time
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job:
    __slots__ = (
        "id",
        "func_name",
        "args",
        "kwargs",
        "status",
        "created_at",
        "retries_left",
        "max_retries",
        "result",
        "error",
    )

    def __init__(self, func_name, args=None, kwargs=None, retries=0):
        self.id = str(uuid.uuid4())
        self.func_name = func_name  # name in task registry
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
            "status": self.status,
            "created_at": self.created_at,
            "retries_left": self.retries_left,
            "max_retries": self.max_retries,
        }
    
    def run(self):
        from nuvom.task import get_task
        self.retries_left -= 1
        task = get_task(self.func_name)
        if not task:
            raise ValueError(f"Task '{self.func_name}' not found.")
        return task(*self.args, **self.kwargs)

    def mark_running(self):
        self.status = JobStatus.RUNNING

    def mark_success(self, result):
        self.status = JobStatus.SUCCESS
        self.result = result

    def mark_failed(self, error):
        self.status = JobStatus.FAILED
        self.error = str(error)
        self.retries_left -= 1

    def can_retry(self):
        return self.retries_left > 0
