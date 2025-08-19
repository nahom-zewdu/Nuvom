# nuvom/discovery/reference.py

"""
Discovery references
====================

This module defines lightweight reference objects produced by the discovery
phase and consumed by the manifest layer and downstream tooling.

Two reference types are exposed:

- TaskReference
  Minimal metadata (file, function name, module name) for normal @task.

- ScheduledTaskReference
  Extends TaskReference with a `metadata` dict copied from the function's
  `_scheduled_metadata` attribute (attached by @scheduled_task decorator).
  This allows persisting *all* scheduling inputs in the manifest so the runtime
  (scheduler) does not need to import user modules to reconstruct schedule state.

Design principles
-----------------
- References are intentionally dumb DTOs (no persistence or scheduling logic).
- Import/loading helpers are kept minimal; discovery should avoid executing
  user code unless strictly necessary. We import scheduled-task modules only
  when we must read `_scheduled_metadata`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class TaskReference:
    """
    Represents metadata about a discovered task (@task).

    Attributes
    ----------
    file_path : str
        Absolute or relative path to the Python source file.
    func_name : str
        Name of the task function.
    module_name : Optional[str] Python module path (dot notation) if known/resolvable.
    """

    def __init__(self, file_path: str, func_name: str, module_name: Optional[str] = None):
        self.file_path = file_path
        self.func_name = func_name
        self.module_name = module_name

    def __repr__(self) -> str:
        return f"<TaskReference {self.module_name or self.file_path}:{self.func_name}>"

    # Kept for dev tooling / debugging convenience
    def load(self) -> Callable:
        """
        Dynamically load the task function.

        Returns
        -------
        Callable
            The task function.

        Raises
        ------
        ImportError
            If the module cannot be imported.
        AttributeError
            If the function name is not found in the module.
        """
        import importlib.util
        import sys

        if self.module_name:
            module = __import__(self.module_name, fromlist=[""])
        else:
            spec = importlib.util.spec_from_file_location("dynamic_task_mod", self.file_path)
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load spec from path: {self.file_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules["dynamic_task_mod"] = module
            spec.loader.exec_module(module)

        func = getattr(module, self.func_name)
        if not callable(func):
            raise AttributeError(f"Attribute '{self.func_name}' in '{module.__name__}' is not callable")
        return func


class ScheduledTaskReference(TaskReference):
    """
    Reference for a scheduled task (@scheduled_task) with attached scheduling metadata.

    Parameters
    ----------
    file_path : str
        Source file path where the function is defined.
    func_name : str
        Function name as discovered.
    module_name : Optional[str]
        Dotted module path (when resolvable).
    metadata : Dict[str, Any]
        A JSON-serializable dict copied from the function’s `_scheduled_metadata`
        (attached by the @scheduled_task decorator). Example:

        {
          "schedule_type": "cron",
          "cron_expr": "0 0 * * *",
          "interval_secs": null,
          "run_at": null,
          "args": [],
          "kwargs": {},
          "enabled": true,
          "misfire_policy": "run_immediately",
          "concurrency_limit": 1,
          "queue_name": "default",
          "timezone": "UTC",
          "task_name": "daily_cleanup"
        }

    Notes
    -----
    - We do not validate correctness here; validation happens later when
      converting into a `ScheduledJob` domain model.
    - Keeping the raw metadata in the manifest prevents import-time side effects
      during scheduler startup.
    """

    def __init__(
        self,
        file_path: str,
        func_name: str,
        module_name: Optional[str],
        metadata: Dict[str, Any],
    ) -> None:
        super().__init__(file_path, func_name, module_name)
        self.metadata: Dict[str, Any] = metadata

    def __repr__(self) -> str:  # pragma: no cover - debug-friendly
        base = super().__repr__()[1:-1]  # strip < >
        return f"<{base} scheduled>"
