# nuvom/job.py

"""
Job object definition and lifecycle management.

The `Job` class represents an executable unit of work in Nuvom.
It encapsulates task metadata, lifecycle state, retries, timeouts,
and result persistence. Both ad-hoc (`@task`) and scheduled
(`@scheduled_task`) jobs are unified under this abstraction.

Key Features
------------
- Status lifecycle tracking (pending → running → success/failed).
- Retry and backoff handling.
- Result/error persistence in configured result backend.
- Support for execution hooks (before, after, on_error).
- Priority-based dispatch (lower = higher priority).
- Serialization for persistence/transport.
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
    """Lifecycle states for a Job."""
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

    Parameters
    ----------
    func_name : str
        Name of the registered task function to execute.
    args : tuple, optional
        Positional arguments for the task (default: ()).
    kwargs : dict, optional
        Keyword arguments for the task (default: {}).
    retries : int, optional
        Maximum retry attempts (default: 0).
    store_result : bool, optional
        Whether to persist results/errors in backend (default: True).
    timeout_secs : int, optional
        Execution time limit in seconds (default: None).
    timeout_policy : {"fail","retry","ignore"}, optional
        Strategy when a timeout occurs (default: from settings).
    retry_delay_secs : int, optional
        Delay before retry in seconds (default: None).
    before_job : callable, optional
        Hook executed before task runs.
    after_job : callable, optional
        Hook executed after successful completion.
    on_error : callable, optional
        Hook executed on failure.

    Scheduling/Priority
    -------------------
    priority : int
        Job dispatch priority. Lower values run first. Default = 5.
        (e.g., scheduled tasks = 1, normal tasks = 5).
    scheduled : bool
        True if created by the scheduler (vs ad-hoc task).
    """

    def __init__(
        self,
        func_name: str,
        args: tuple = (),
        kwargs: dict | None = None,
        *,
        retries: int = 0,
        store_result: bool = True,
        timeout_secs: int | None = None,
        timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
        retry_delay_secs: int | None = None,
        before_job: Optional[Callable[[], None]] = None,
        after_job: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        priority: int = 5,
        scheduled: bool = False,
    ):
        # Core identifiers
        self.id = str(uuid.uuid4())
        self.func_name = func_name
        self.args = args or ()
        self.kwargs = kwargs or {}

        # Execution/lifecycle state
        self.status = JobStatus.PENDING
        self.created_at = time.time()
        self.result: Any = None
        self.error: str | None = None

        # Retry/timeout config
        self.max_retries = retries
        self.retries_left = retries
        self.timeout_secs = timeout_secs
        self.retry_delay_secs = retry_delay_secs
        self.timeout_policy = timeout_policy or get_settings().timeout_policy
        self.next_retry_at: float | None = None

        # Persistence
        self.store_result = store_result

        # Scheduling/priority
        self.priority = priority
        self.scheduled = scheduled

        # Hooks
        self.before_job = before_job
        self.after_job = after_job
        self.on_error = on_error

        logger.debug(
            f"[job:{self.id}] Created "
            f"{'scheduled ' if self.scheduled else ''}job "
            f"for task '{self.func_name}' (priority={self.priority})"
        )

    # ---------------------------------------------------------------- #
    # Serialization
    # ---------------------------------------------------------------- #
    def to_dict(self) -> dict:
        """Serialize job state to dictionary."""
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
            "priority": self.priority,
            "scheduled": self.scheduled,
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
            priority=data.get("priority", 5),
            scheduled=data.get("scheduled", False),
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

        Raises
        ------
        TimeoutError
            If no result available within timeout.
        RuntimeError
            If an error was stored for this job.
        """
        if not self.store_result:
            logger.warning(f"[job:{self.id}] get() called on non-persistent job.")
            return {}

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
                raise TimeoutError(
                    f"[job:{self.id}] Result not ready within {timeout} seconds."
                )

            time.sleep(interval)

    def mark_running(self):
        """Mark job as running."""
        self.status = JobStatus.RUNNING
        logger.debug(f"[job:{self.id}] Status set to RUNNING.")

    def mark_success(self, result: Any):
        """Mark job as successfully completed."""
        self.status = JobStatus.SUCCESS
        self.result = result
        logger.debug(f"[job:{self.id}] Status set to SUCCESS.")

    def mark_failed(self, error: Exception):
        """Mark job as failed with error message."""
        self.status = JobStatus.FAILED
        self.error = str(error)
        logger.error(f"[job:{self.id}] Status set to FAILED. Error: {error}")

    def can_retry(self) -> bool:
        """Return True if job has retries left."""
        return self.retries_left > 0
