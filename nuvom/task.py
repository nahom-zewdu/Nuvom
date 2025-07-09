# nuvom/task.py
"""
Task decorator & runtime wrapper for Nuvom.

Adds:
• Safe defaults from global settings (timeout, retry delay)
• Strict tag validation → always List[str]
• Thread-safe registry check
• map() now accepts any iterable of arg-sequences
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Iterable, Sequence
from typing import Any, Callable, List, Literal, Optional

from nuvom.config import get_settings
from nuvom.job import Job
from nuvom.queue import get_queue_backend
from nuvom.registry.registry import get_task_registry


# -------------------------------------------------------------------- #
# Helper utilities
# -------------------------------------------------------------------- #
def _coerce_tags(raw: Any | None) -> List[str]:
    """Ensure tags is always a list of strings."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, Iterable):
        coerced = []
        for t in raw:
            if not isinstance(t, str):
                raise TypeError("All tags must be strings.")
            coerced.append(t)
        return coerced
    raise TypeError("tags must be str, List[str], or None.")


def _default_timeout(provided: int | None) -> int | None:
    """Fallback to global setting if task‐specific timeout is None."""
    return provided if provided is not None else get_settings().job_timeout_secs


def _default_retry_delay(provided: int | None) -> int | None:
    """Fallback to global retry delay if not explicitly set."""
    return provided if provided is not None else get_settings().retry_delay_secs


# -------------------------------------------------------------------- #
# Task wrapper
# -------------------------------------------------------------------- #
class Task:
    """
    Wrapper enabling `.delay()` and `.map()` execution for a Python function.

    Handles:
    • Registry registration with metadata
    • Retry / timeout defaults
    • Optional lifecycle hooks: before_job / after_job / on_error
    """

    def __init__(
        self,
        func: Callable,
        *,
        name: Optional[str] = None,
        retries: int = 0,
        store_result: bool = True,
        timeout_secs: Optional[int] = None,
        timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
        retry_delay_secs: int | None = None,
        tags: Optional[list[str] | str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        before_job: Optional[Callable[[], None]] = None,
        after_job: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        functools.update_wrapper(self, func)

        # Core metadata ------------------------------------------------- #
        self.func = func
        self.name = name or func.__name__
        self.retries = retries
        self.store_result = store_result

        self.timeout_secs = _default_timeout(timeout_secs)
        self.retry_delay_secs = _default_retry_delay(retry_delay_secs)
        self.timeout_policy = timeout_policy

        # Optional metadata -------------------------------------------- #
        self.tags = _coerce_tags(tags)
        self.description = description or ""
        self.category = category or "default"

        # Lifecycle hooks ---------------------------------------------- #
        self.before_job = before_job
        self.after_job = after_job
        self.on_error = on_error

        self._register()

    # ---------------------------------------------------------------- #
    # Internal helpers
    # ---------------------------------------------------------------- #
    def _register(self) -> None:
        """Register the task in the global registry (silent=dupes allowed)."""
        if self.name.startswith("test_"):
            warnings.warn(
                f"Task '{self.name}' may interfere with pytest collection.",
                stacklevel=3,
            )
        get_task_registry().register(
            self.name,
            self,
            silent=True,
            metadata={
                "tags": self.tags,
                "description": self.description,
                "category": self.category,
            },
        )

    # ---------------------------------------------------------------- #
    # Invocation helpers
    # ---------------------------------------------------------------- #
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs) -> Job:
        """Enqueue a single job instance and return its Job object."""
        job = Job(
            func_name=self.name,
            args=args,
            kwargs=kwargs,
            retries=self.retries,
            store_result=self.store_result,
            timeout_secs=self.timeout_secs,
            retry_delay_secs=self.retry_delay_secs,
            timeout_policy=self.timeout_policy,
            before_job=self.before_job,
            after_job=self.after_job,
            on_error=self.on_error,
        )
        get_queue_backend().enqueue(job)
        return job

    # Alias for API symmetry
    submit = delay

    def map(self, arg_tuples: Iterable[Sequence[Any]]) -> list[Job]:
        """
        Enqueue multiple jobs given an iterable of positional-arg sequences.

        Example:
            add.map([(1, 2), (3, 4)])
        """
        jobs: list[Job] = []
        for args in arg_tuples:
            if not isinstance(args, Sequence):
                raise TypeError("Each element passed to map() must be a sequence.")
            jobs.append(self.delay(*args))
        return jobs

    # ---------------------------------------------------------------- #
    # Nice repr for debugging
    # ---------------------------------------------------------------- #
    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Task {self.name} "
            f"retries={self.retries} "
            f"timeout={self.timeout_secs}s "
            f"tags={self.tags}>"
        )


# -------------------------------------------------------------------- #
# Decorator factory
# -------------------------------------------------------------------- #
def task(
        _func: Callable | None = None,
        *,
        name: Optional[str] = None,
        retries: int = 0,
        store_result: bool = True,
        timeout_secs: Optional[int] = None,
        timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
        retry_delay_secs: int | None = None,
        tags: list[str] | str | None = None,
        description: str | None = None,
        category: str | None = None,
        before_job: Optional[Callable[[], None]] = None,
        after_job: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
    """
    Decorator that converts a regular function into a Nuvom Task.

    Usage:
        @task
        def foo(): ...

        @task(retries=2, tags=["math"])
        def bar(x, y): ...
    """

    def decorator(func: Callable) -> Task:
        return Task(
            func,
            name=name,
            retries=retries,
            store_result=store_result,
            timeout_secs=timeout_secs,
            timeout_policy=timeout_policy,
            retry_delay_secs=retry_delay_secs,
            tags=tags,
            description=description,
            category=category,
            before_job=before_job,
            after_job=after_job,
            on_error=on_error,
        )

    return decorator if _func is None else decorator(_func)


# -------------------------------------------------------------------- #
# Public helper
# -------------------------------------------------------------------- #
def get_task(name: str) -> Optional[Task]:
    """Return a registered Task by name (None if missing)."""
    return get_task_registry().get(name)
