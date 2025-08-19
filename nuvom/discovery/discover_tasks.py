# nuvom/discovery/discover_tasks.py

"""
Task & Scheduled Task discovery
===============================

Core logic to scan a directory tree and discover:
- @task               → TaskReference
- @scheduled_task     → ScheduledTaskReference (with `_scheduled_metadata`)

Why two passes?
---------------
We first use a *static* parser (no import) to identify function names and which
decorator appears on them. For **scheduled tasks only**, we then import the
module *safely* to read the attached `_scheduled_metadata` dict from the function.

This hybrid approach preserves safety & speed (no blanket imports) while still
capturing complete scheduling configuration for persistence in the manifest.

Public API
----------
discover_tasks(root_path, include, exclude) -> (List[TaskReference], List[ScheduledTaskReference])
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Any
from pathlib import Path

from nuvom.discovery.walker import get_python_files
from nuvom.discovery.parser import find_task_defs
from nuvom.discovery.compute_path import compute_module_path
from nuvom.discovery.reference import TaskReference, ScheduledTaskReference
from nuvom.log import get_logger

# Prefer the project’s loader util if present (avoids module name collisions).
try:
    from nuvom.discovery.loader import load_module_from_path
except Exception:  # pragma: no cover - fallback path loader
    load_module_from_path = None  # type: ignore

import importlib
import importlib.util
import sys

logger = get_logger()


def _load_module(module_name: str | None, file_path: str):
    """
    Load a module either by its dotted name or from file path (without polluting user modules).

    We prefer:
    1) normal import (fast, uses sys.meta_path)
    2) project loader's load_module_from_path (creates unique name)
    3) vanilla importlib.util.spec_from_file_location

    Returns
    -------
    module : ModuleType
    """
    # 1) Try regular import by module name
    if module_name:
        try:
            return importlib.import_module(module_name)
        except Exception as e:
            logger.debug("[discover] Import by module name failed for %s: %s", module_name, e)

    # 2) Use project loader if available
    if load_module_from_path is not None:
        return load_module_from_path(file_path)

    # 3) Fallback: direct path import with a unique-ish name
    mod_name = f"nuvom_discovery_{abs(hash(file_path))}"
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load spec from path: {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def _extract_scheduled_metadata(module, func_name: str) -> Dict[str, Any] | None:
    """
    Best-effort extraction of `_scheduled_metadata` from a function in a module.

    Returns
    -------
    dict | None
        The metadata dict if present and well-formed; otherwise None.
    """
    if not hasattr(module, func_name):
        logger.warning("[discover] Module %s has no attribute '%s'", getattr(module, "__name__", "?"), func_name)
        return None

    func = getattr(module, func_name)
    if not callable(func):
        logger.warning("[discover] Attribute '%s' in %s is not callable", func_name, getattr(module, "__name__", "?"))
        return None

    meta = getattr(func, "_scheduled_metadata", None)
    if meta is None:
        logger.warning("[discover] scheduled_task '%s' has no _scheduled_metadata; skipping metadata.", func_name)
        return None

    if not isinstance(meta, dict):
        logger.warning("[discover] _scheduled_metadata for '%s' is not a dict; skipping.", func_name)
        return None

    # Shallow copy to ensure JSON-serializable primitive containers downstream
    return dict(meta)


def discover_tasks(
    root_path: str = ".",
    include: List[str] | None = None,
    exclude: List[str] | None = None,
) -> Tuple[List[TaskReference], List[ScheduledTaskReference]]:
    """
    Discover both @task and @scheduled_task in the codebase.

    Parameters
    ----------
    root_path : str
        Directory root to scan (recursively).
    include : List[str] | None
        Optional glob patterns to include.
    exclude : List[str] | None
        Optional glob patterns to exclude.

    Returns
    -------
    (normal_tasks, scheduled_tasks)
        normal_tasks: List[TaskReference]
        scheduled_tasks: List[ScheduledTaskReference]

    Notes
    -----
    - Static parse via `find_task_defs` avoids import-time side effects.
    - Only scheduled-task modules are imported (best-effort) to read metadata.
    """
    include = include or []
    exclude = exclude or []

    normal_tasks: List[TaskReference] = []
    scheduled_tasks: List[ScheduledTaskReference] = []

    files = get_python_files(root_path, include, exclude)
    root = Path(root_path).resolve()

    for file in files:
        task_defs = find_task_defs(file)  # [(func_name, decorator_type)]
        if not task_defs:
            continue

        for func_name, decorator_type in task_defs:
            module_path = compute_module_path(file, root_path=root)

            if decorator_type == "task":
                normal_tasks.append(TaskReference(str(file), func_name, module_path))
                continue

            if decorator_type == "scheduled_task":
                # Import the module ONLY to read the function's `_scheduled_metadata`
                try:
                    module = _load_module(module_path, str(file))
                    meta = _extract_scheduled_metadata(module, func_name) or {}
                except Exception as e:
                    logger.exception("[discover] Failed reading _scheduled_metadata for %s:%s", module_path or file, func_name)
                    meta = {}

                # Ensure task_name is present for consumers; default to func name
                meta.setdefault("task_name", func_name)

                scheduled_tasks.append(
                    ScheduledTaskReference(
                        file_path=str(file),
                        func_name=func_name,
                        module_name=module_path,
                        metadata=meta,
                    )
                )

    return normal_tasks, scheduled_tasks
