# nuvom/job.py

"""
Job object definition and lifecycle management.

Handles:
• Retry control
• Status lifecycle
• Result/error serialization
• Lifecycle hooks
"""

import uuid
import time
from enum import Enum
from typing import Any, Callable, Literal, Optional

from nuvom.config import get_settings
from nuvom.log import get_logger
from nuvom.result_store import get_backend

logger = get_logger()


# -------------------------------------------------------------------- #
# Enums
# -------------------------------------------------------------------- #
class JobStatus(str, Enum):
    """Job state lifecycle."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# -------------------------------------------------------------------- #
# Job class
# -------------------------------------------------------------------- #
class Job:
    """
    Represents a single executable task (with metadata, status, retry logic).

    Fields:
        • func_name — name of registered task
        • args/kwargs — execution parameters
        • retries — max attempts for failure handling
        • status/result/error — runtime tracking
        • store_result — persist result/error in backend
        • timeout_secs — execution time limit
        • retry_delay_secs — delay before retry
        • timeout_policy — fail, retry, or ignore on timeout
        • hooks — before/after/error lifecycle hooks
    """

    def __init__(
        self,
        func_name: str,
        args: tuple = (),
        kwargs: dict = None,
        *,
        retries: int = 0,
        store_result: bool = True,
        timeout_secs: int | None = None,
        timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
        retry_delay_secs: int | None = None,
        before_job: Optional[Callable[[], None]] = None,
        after_job: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.func_name = func_name
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.store_result = store_result
        self.status = JobStatus.PENDING
        self.created_at = time.time()

        self.timeout_secs = timeout_secs
        self.retry_delay_secs = retry_delay_secs
        self.timeout_policy = timeout_policy or get_settings().timeout_policy

        self.max_retries = retries
        self.retries_left = retries
        self.result: Any = None
        self.error: str | None = None
        self.next_retry_at: float | None = None

        self.before_job = before_job
        self.after_job = after_job
        self.on_error = on_error

        logger.debug(f"[job:{self.id}] Created job for task '{self.func_name}'")

    # ---------------------------------------------------------------- #
    # Serialization
    # ---------------------------------------------------------------- #
    def to_dict(self) -> dict:
        """Serialize job state."""
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
            "retry_delay_secs": self.retry_delay_secs,
            "next_retry_at": self.next_retry_at,
            "timeout_policy": self.timeout_policy,
            "hooks": {
                "before_job": bool(self.before_job),
                "after_job": bool(self.after_job),
                "on_error": bool(self.on_error),
            },
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Restore a job from serialized dict."""
        job = cls(
            func_name=data["func_name"],
            args=tuple(data.get("args", ())),
            kwargs=data.get("kwargs", {}),
            retries=data.get("max_retries", 0),
            store_result=data.get("store_result", True),
            timeout_secs=data.get("timeout_secs"),
            retry_delay_secs=data.get("retry_delay_secs"),
            timeout_policy=data.get("timeout_policy"),
        )
        job.id = data.get("id", job.id)
        job.status = JobStatus(data.get("status", "PENDING"))
        job.created_at = data.get("created_at", time.time())
        job.retries_left = data.get("retries_left", job.max_retries)
        job.result = data.get("result")
        job.error = data.get("error")
        job.next_retry_at = data.get("next_retry_at")
        return job

    # ---------------------------------------------------------------- #
    # Lifecycle
    # ---------------------------------------------------------------- #
    def run(self):
        """Execute the task registered under `func_name`."""
        from nuvom.task import get_task

        task = get_task(self.func_name)
        if not task:
            raise ValueError(f"Task '{self.func_name}' not found")

        logger.debug(f"[job:{self.id}] Running with args={self.args} kwargs={self.kwargs}")
        return task(*self.args, **self.kwargs)

    def get(self, timeout: float | None = None, interval: float = 0.5) -> dict:
        """
        Poll result from backend until available or timeout hit.

        Raises:
            TimeoutError | RuntimeError
        """
        if not self.store_result:
            logger.warning(f"[job:{self.id}] get() called on non-persistent job.")
            return

        backend = get_backend()
        start = time.time()

        while True:
            result = backend.get_result(self.id)
            if result is not None:
                logger.debug(f"[job:{self.id}] Result retrieved.")
                return self.to_dict()

            error = backend.get_error(self.id)
            if error is not None:
                raise RuntimeError(f"[job:{self.id}] Failed: {error}")

            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError(f"[job:{self.id}] Result not ready within {timeout} seconds.")

            time.sleep(interval)

    def mark_running(self):
        self.status = JobStatus.RUNNING
        logger.debug(f"[job:{self.id}] Status set to RUNNING.")

    def mark_success(self, result: Any):
        self.status = JobStatus.SUCCESS
        self.result = result
        logger.debug(f"[job:{self.id}] Status set to SUCCESS.")

    def mark_failed(self, error: Exception):
        self.status = JobStatus.FAILED
        self.error = str(error)
        logger.error(f"[job:{self.id}] Status set to FAILED. Error: {error}")

    def can_retry(self) -> bool:
        return self.retries_left > 0
