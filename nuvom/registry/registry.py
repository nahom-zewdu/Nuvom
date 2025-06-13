# nuvom/registry/registry.py

import threading
from typing import Callable, Dict, Optional


class TaskRegistry:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._tasks: Dict[str, Callable] = {}
        self._registry_lock = threading.Lock()

    def register(self, name: str, func: Callable, force: bool=False):
        with self._registry_lock:
            if name in self._tasks and not force:
                return  # Already registered
            self._tasks[name] = func

    def get(self, name: str) -> Optional[Callable]:
        return self._tasks.get(name)

    def all(self) -> Dict[str, Callable]:
        return dict(self._tasks)

    def clear(self):
        with self._registry_lock:
            self._tasks.clear()


def get_task_registry() -> TaskRegistry:
    if TaskRegistry._instance is None:
        with TaskRegistry._lock:
            if TaskRegistry._instance is None:
                TaskRegistry._instance = TaskRegistry()
    return TaskRegistry._instance
