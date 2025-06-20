# nuvom/registry/registry.py

"""
Global task registry for storing and managing task functions and their metadata.

Supports singleton access, thread-safe registration, metadata storage,
and conflict handling (force/silent modes).
"""

import threading
from typing import Callable, Dict, Optional, Any
from dataclasses import dataclass
from nuvom.log import logger


@dataclass
class TaskInfo:
    """
    Represents a registered task's function and its associated metadata.

    Attributes:
        func: The callable representing the task.
        metadata: Optional metadata dictionary associated with the task.
    """
    func: Callable
    metadata: Dict[str, Any]


class TaskRegistry:
    """
    Thread-safe registry for managing task functions globally.

    Supports singleton instance creation and provides methods
    for registering, retrieving, and clearing task entries.

    Methods:
        register(name, func, *, metadata, force, silent): Register a task.
        get(name): Retrieve a task function by name.
        get_metadata(name): Retrieve task metadata by name.
        all(): Return all registered tasks.
        clear(): Remove all registered tasks.
    """

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

        Args:
            name: The name of the task.
            func: The function representing the task.
            metadata: Optional metadata dictionary.
            force: If True, overwrite existing task.
            silent: If True, skip duplicates without error.

        Raises:
            ValueError: If task name already exists and neither force nor silent is True.
        """
        metadata = metadata or {}
        with self._registry_lock:
            if name in self._tasks:
                if force:
                    logger.debug(f"[registry] Overwriting task '{name}' due to force=True.")
                    self._tasks[name] = TaskInfo(func=func, metadata=metadata)
                    return
                elif silent:
                    logger.debug(f"[registry] Skipping duplicate task '{name}' due to silent=True.")
                    return
                else:
                    raise ValueError(f"Task name '{name}' already registered.")
            self._tasks[name] = TaskInfo(func=func, metadata=metadata)
            logger.debug(f"[registry] Registered task '{name}'.")

    def get(self, name: str) -> Optional[Callable]:
        """
        Retrieve a task function by name.

        Args:
            name: Name of the task.

        Returns:
            The registered function, or None if not found.
        """
        task_info = self._tasks.get(name)
        return task_info.func if task_info else None

    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for a task.

        Args:
            name: Name of the task.

        Returns:
            The metadata dictionary, or None if not found.
        """
        task_info = self._tasks.get(name)
        return task_info.metadata if task_info else None

    def all(self) -> Dict[str, TaskInfo]:
        """
        Get all registered tasks and their metadata.

        Returns:
            A dictionary of task names to TaskInfo objects.
        """
        return dict(self._tasks)

    def clear(self):
        """
        Clear all registered tasks from the registry.
        """
        with self._registry_lock:
            self._tasks.clear()
            logger.debug("[registry] Cleared all tasks.")


def get_task_registry() -> TaskRegistry:
    """
    Accessor for the global singleton instance of TaskRegistry.

    Returns:
        The singleton TaskRegistry instance.
    """
    if TaskRegistry._instance is None:
        with TaskRegistry._lock:
            if TaskRegistry._instance is None:
                TaskRegistry._instance = TaskRegistry()
                logger.debug("[registry] Created global TaskRegistry instance.")
    return TaskRegistry._instance
