# nuvom/registry.py

# let @task auto-register task functions so workers can call them by name.

from typing import Callable, Dict, Optional

_task_registry: Dict[str, Callable] = {}


def task(fn: Optional[Callable] = None, *, name: Optional[str] = None):
    """
    Decorator to mark a function as a Nuvom task.
    Registers the function in the global task registry.
    """
    def decorator(func: Callable):
        task_name = name or func.__name__
        if task_name in _task_registry:
            raise ValueError(f"Task name '{task_name}' already registered.")
        _task_registry[task_name] = func
        return func

    # Handle both @task and @task()
    if fn is None:
        return decorator
    return decorator(fn)


def resolve_task(name: str) -> Callable:
    if name not in _task_registry:
        raise KeyError(f"Task '{name}' not found in registry.")
    return _task_registry[name]


def list_tasks() -> Dict[str, Callable]:
    return dict(_task_registry)
