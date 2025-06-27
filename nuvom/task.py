# nuvom/task.py

from typing import Callable, Optional, Any, List, Literal
import functools
import warnings

from nuvom.registry.registry import get_task_registry
from nuvom.job import Job
from nuvom.queue import get_queue_backend


class Task:
    """
    Represents a task wrapper that enables delayed and mapped execution.
    Handles registration, retries, lifecycle hooks, and result persistence.
    Supports optional metadata (description, tags, category)
    """

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        retries: int = 0,
        store_result: bool = True,
        timeout_secs: Optional[int] = None,
        timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
        retry_delay_secs: int | None = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        before_job: Optional[Callable[[], None]] = None,
        after_job: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """
        Wraps a Python function as a Nuvom task with metadata and execution options.
        """
        functools.update_wrapper(self, func)

        self.func = func
        self.name = name or func.__name__
        self.retries = retries
        self.store_result = store_result
        self.timeout_secs = timeout_secs
        self.retry_delay_secs = retry_delay_secs
        self.timeout_policy = timeout_policy
        
        self.tags = tags or []
        self.description = description or ""
        self.category = category or "default"

        self.before_job = before_job
        self.after_job = after_job
        self.on_error = on_error

        # Register the task in the global registry
        self._register()

    def _register(self):
        if self.name.startswith("test_"):
            warnings.warn(
                f"Task '{self.name}' may interfere with pytest collection.", stacklevel=3
            )
        get_task_registry().register(self.name, self, silent=True, metadata={
            "tags": self.tags,
            "description": self.description,
            "category": self.category,
        })

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs) -> Job:
        job = Job(
            func_name=self.name,
            args=args,
            kwargs=kwargs,
            retries=self.retries,
            store_result=self.store_result,
            timeout_secs=self.timeout_secs,
            retry_delay_secs = self.retry_delay_secs    
            timeout_policy = self.timeout_policy
            before_job=self.before_job,
            after_job=self.after_job,
            on_error=self.on_error,
        )
        get_queue_backend().enqueue(job)
        return job

    def submit(self, *args, **kwargs) -> Job:
        return self.delay(*args, **kwargs)

    def map(self, arg_tuples) -> list[Job]:
        jobs = []
        for args in arg_tuples:
            if not isinstance(args, (list, tuple)):
                raise TypeError("Each map() argument must be a tuple or list.")
            jobs.append(self.delay(*args))
        return jobs


def task(
    _func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    retries: int = 0,
    store_result: bool = True,
    timeout_secs: Optional[int] = None,
    timeout_policy: Literal["fail", "retry", "ignore"] | None = None,
    retry_delay_secs: int | None = None,
    tags=None,
    description=None,
    category= None,
    before_job: Optional[Callable[[], None]] = None,
    after_job: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
):
    """
    Task decorator that wraps a function as a background-executable task.
    Can be used with or without parameters.
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

    if _func is None:
        return decorator
    else:
        return decorator(_func)


def get_task(name: str) -> Optional[Task]:
    """
    Lookup a registered task by name.
    """
    return get_task_registry().get(name)
