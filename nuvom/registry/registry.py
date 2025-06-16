# nuvom/registry/registry.py

import threading
from typing import Callable, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class TaskInfo:
    """Container for a registered task's callable and its metadata."""
    func: Callable
    metadata: Dict[str, Any]


class TaskRegistry:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
        self._registry_lock = threading.Lock()

    def register(
        self,
        name: str,
        func: Callable,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False,
        silent: bool = False
    ):
        """
        Register a task by name with optional metadata.

        - If `force=True`, overwrite existing task.
        - If `silent=True`, skip duplicates silently.
        - By default, raises ValueError on name conflict.
        """
        metadata = metadata or {}
        with self._registry_lock:
            if name in self._tasks:
                if force:
                    self._tasks[name] = TaskInfo(func=func, metadata=metadata)
                    return
                elif silent:
                    return
                else:
                    raise ValueError(f"Task name '{name}' already registered.")
            self._tasks[name] = TaskInfo(func=func, metadata=metadata)

    def get(self, name: str) -> Optional[Callable]:
        task_info = self._tasks.get(name)
        return task_info.func if task_info else None

    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        task_info = self._tasks.get(name)
        return task_info.metadata if task_info else None

    def all(self) -> Dict[str, TaskInfo]:
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
