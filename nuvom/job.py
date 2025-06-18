# nuvom/job.py

import uuid
import time
from enum import Enum
from typing import Callable, Optional, Any

from nuvom.log import logger
from nuvom.result_store import get_backend


class JobStatus(str, Enum):
    """Enumeration of possible job states in Nuvom's lifecycle."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job:
    """
    Represents a single task execution request with metadata and lifecycle hooks.
    
    Args:
        func_name: Name of the registered task to execute
        args: Positional arguments for the task
        kwargs: Keyword arguments for the task
        retries: Number of times to retry on failure
        store_result: Whether to persist result/error in backend
        timeout_secs: Optional execution timeout in seconds
        before_job, after_job, on_error: Optional lifecycle hooks
    """
    def __init__(self, func_name, 
                 args=None, kwargs=None, 
                 retries=0, store_result=True, 
                 timeout_secs=None, 
                 before_job: Optional[Callable[[], None]] = None, 
                 after_job: Optional[Callable[[Any], None]] = None, 
                 on_error: Optional[Callable[[Exception], None]] = None
                ):
        self.id = str(uuid.uuid4())
        self.func_name = func_name
        self.store_result = store_result
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.timeout_secs = timeout_secs
        self.status = JobStatus.PENDING
        self.created_at = time.time()
        self.retries_left = retries
        self.max_retries = retries
        self.result = None
        self.error = None
        
        self.before_job = before_job
        self.after_job = after_job
        self.on_error = on_error

        logger.debug(f"[job:{self.id}] Created job for task '{self.func_name}'")

    def to_dict(self):
        """Serialize job state to a dictionary."""
        return {
            "id": self.id,
            "func_name": self.func_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "timeout_secs": self.timeout_secs,
            "store_result": self.store_result,
            "status": self.status,
            "created_at": self.created_at,
            "retries_left": self.retries_left,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error,
            "hooks": {
                "before_job": bool(self.before_job),
                "after_job": bool(self.after_job),
                "on_error": bool(self.on_error),
            },
        }

    @classmethod
    def from_dict(cls, data):
        """Restore a Job from its serialized dictionary form."""
        job = cls(
            func_name=data["func_name"],
            args=tuple(data.get("args")),
            kwargs=data.get("kwargs"),
            timeout_secs=data.get("timeout_secs"),
            retries=data.get("max_retries", 0),
            store_result=data.get("store_result", True),
        )
        job.id = data.get("id")
        job.status = data.get("status", JobStatus.PENDING)
        job.created_at = data.get("created_at", time.time())
        job.retries_left = data.get("retries_left", job.max_retries)
        job.result = data.get("result")
        job.error = data.get("error")
        return job

    def run(self):
        """
        Run the registered task associated with this job.
        
        Returns:
            Result of the task execution.
        
        Raises:
            ValueError if task is not found in registry.
        """
        from nuvom.task import get_task

        self.retries_left -= 1
        task = get_task(self.func_name)
        if not task:
            raise ValueError(f"Task '{self.func_name}' not found.")
        
        logger.debug(f"[job:{self.id}] Executing task '{self.func_name}' with args={self.args} kwargs={self.kwargs}")
        return task(*self.args, **self.kwargs)

    def get(self, timeout=None, interval=0.5):
        """
        Polls for result. Blocks until result is available or timeout is hit.
        
        Args:
            timeout: Optional timeout in seconds
            interval: Polling interval in seconds
        
        Returns:
            Job state dict if result is ready
        
        Raises:
            TimeoutError, RuntimeError
        """
        if not self.store_result:
            logger.warning(f"[job:{self.id}] get() called on non-persistent job.")
            return

        backend = get_backend()
        start = time.time()

        while True:
            result = backend.get_result(self.id)
            if result is not None:
                logger.debug(f"[job:{self.id}] Result ready.")
                return self.to_dict()

            error = backend.get_error(self.id)
            if error is not None:
                raise RuntimeError(f"Job failed: {error}")

            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError("Job result not ready within timeout")

            time.sleep(interval)

    def mark_running(self):
        """Mark job as running."""
        self.status = JobStatus.RUNNING
        logger.debug(f"[job:{self.id}] Marked as RUNNING.")

    def mark_success(self, result):
        """Mark job as successfully completed with result."""
        self.status = JobStatus.SUCCESS
        self.result = result
        logger.debug(f"[job:{self.id}] Marked as SUCCESS.")

    def mark_failed(self, error):
        """Mark job as failed with error."""
        self.status = JobStatus.FAILED
        self.error = str(error)
        logger.error(f"[job:{self.id}] Marked as FAILED. Error: {error}")

    def can_retry(self):
        """Return True if job is eligible for retry."""
        return self.retries_left > 0