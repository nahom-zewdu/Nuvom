# nuvom/task.py

from typing import Callable, Optional, Any
import functools
import warnings

from nuvom.registry import REGISTRY
from nuvom.job import Job
from nuvom.queue import get_queue_backend

class Task:
    def __init__(self, 
                 func, 
                 name=None, 
                 retries=0, 
                 store_result=True, 
                 timeout_secs=None,
                 before_job: Optional[Callable[[], None]] = None, 
                 after_job: Optional[Callable[[Any], None]] = None, 
                 on_error: Optional[Callable[[Exception], None]] = None
                 ):
        self.func = func
        self.name = name or func.__name__
        if self.name.startswith("test_"):
            warnings.warn(
                f"Task '{self.name}' may shadow pytest test function collection",
                stacklevel=2
            )
        
        self.retries = retries
        self.store_result = store_result
        self.timeout_secs = timeout_secs
        
        self.before_job = before_job
        self.after_job = after_job
        self.on_error = on_error
        
        REGISTRY.register(self)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        job = Job(
            func_name=self.name, 
            args=args,
            kwargs=kwargs, 
            retries=self.retries, 
            store_result=self.store_result, 
            timeout_secs=self.timeout_secs,
            before_job=self.before_job,
            after_job=self.after_job,
            on_error=self.on_error,
        )
        queue = get_queue_backend()
        queue.enqueue(job)
        
        print("Job queued ", self.name, args)
        return job
    
    def submit(self, *args, **kwargs):
        return self.delay(*args, **kwargs)
    
    def map(self, arg_tuples):
        """
        Enqueue multiple jobs in batch using a list of argument tuples.
        """
        jobs = []
        for args in arg_tuples:
            if not isinstance(args, (list, tuple)):
                raise TypeError("Each map item must be a tuple or list of arguments")
            jobs.append(self.delay(*args))
        return jobs


def task(_func=None, *, name=None, retries=0, store_result=True, before_job=None, after_job=None, on_error=None):
    def wrapper(func):
        return Task(
            func,
            name=name,
            retries=retries,
            store_result=store_result,
            before_job=before_job,
            after_job=after_job,
            on_error=on_error
        )

    if _func is None:
        return wrapper
    else:
        return wrapper(_func)


def get_task(name):
    return REGISTRY.get(name)
