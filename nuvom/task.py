# Parses the @task decorator
# Registers task metadata
# Handles retries and delay logic


# nuvom/task.py

import functools
from .job import Job
from .queue import get_global_queue

_TASK_REGISTRY = {}

class Task:
    def __init__(self, func, name=None, retries=0):
        self.func = func
        self.name = name or func.__name__
        self.retries = retries
        _TASK_REGISTRY[self.name] = self

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        job = Job(func_name=self.name, args=args, kwargs=kwargs, retries=self.retries)
        queue = get_global_queue()
        queue.enqueue(job)
        return job.id
    
    def submit(self, *args, **kwargs):
        return self.delay(*args, **kwargs)


def task(_func=None, *, name=None, retries=0):
    def wrapper(func):
        return Task(func, name=name, retries=retries)

    if _func is None:
        return wrapper
    else:
        return wrapper(_func)

def get_task(name):
    return _TASK_REGISTRY.get(name)
