# Parses the @task decorator
# Registers task metadata
# Handles retries and delay logic


# nuvom/task.py

import functools
from nuvom.job import Job
from nuvom.queue import get_global_queue

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
    
def task(_func=None, *, name=None, retries=0):
    def wrapper(func):
        return Task(func, name=name, retries=retries)

    if _func is None:
        return wrapper
    else:
        return wrapper(_func)

def get_task(name):
    return _TASK_REGISTRY.get(name)
