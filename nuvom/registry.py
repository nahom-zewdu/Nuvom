# nuvom/registry.py

from threading import RLock

class TaskRegistry:
    _instance = None
    _lock = RLock()
    # _tasks = {}

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._tasks = {}
            return cls._instance

    def register(self, task):
        with self._lock:
            if task.name in self._tasks:
                raise ValueError(f"Task '{task.name}' is already registered.")
            self._tasks[task.name] = task

    def get(self, name):
        with self._lock:
            return self._tasks.get(name)

    def all(self):
        with self._lock:
            return list(self._tasks.values())

# Global instance used by everything
REGISTRY = TaskRegistry()
