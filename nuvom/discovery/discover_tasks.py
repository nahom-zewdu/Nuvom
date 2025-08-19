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

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

from nuvom.discovery.walker import get_python_files
from nuvom.discovery.parser import find_task_defs
from nuvom.discovery.compute_path import compute_module_path
from nuvom.discovery.reference import TaskReference, ScheduledTaskReference
from nuvom.log import get_logger

try:
    # Prefer project’s loader util if available
    from nuvom.discovery.loader import load_module_from_path
except Exception:  # pragma: no cover
    load_module_from_path = None  # type: ignore

logger = get_logger()


# --------------------------- module import helpers ---------------------------
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
    if module_name:
        try:
            return importlib.import_module(module_name)
        except Exception as e:
            logger.debug("[discover] Import by module name failed for %s: %s", module_name, e)

    if load_module_from_path is not None:
        return load_module_from_path(file_path)

    # Fallback: synthetic unique name
    mod_name = f"nuvom_discovery_{abs(hash(file_path))}"
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot create import spec for: {file_path}")

    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader
    sys.modules[mod_name] = module
    try:
        loader.exec_module(module)
        return module
    finally:
        # avoid permanent pollution
        sys.modules.pop(mod_name, None)


# ----------------------- scheduled metadata extraction -----------------------
def _extract_scheduled_metadata(module, func_name: str) -> Dict[str, Any] | None:
    """
    Extract `_scheduled_metadata` from a function in a module.

    Returns
    -------
    dict | None
        The metadata dict if present and well-formed; otherwise None.
    """
    func = getattr(module, func_name, None)
    if not callable(func):
        logger.debug("[discover] %s.%s is not callable", getattr(module, "__name__", "?"), func_name)
        return None

    meta = getattr(func, "_scheduled_metadata", None)
    if meta is None:
        return None
    if not isinstance(meta, dict):
        logger.warning("[discover] _scheduled_metadata for '%s' is not a dict; skipping.", func_name)
        return None

    # Normalize → shallow copy for downstream JSON safety
    return dict(meta)

# ------------------------------ public API -----------------------------------
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
        defs = find_task_defs(file)
        if not defs:
            continue

        for func_name, decorator_type in defs:
            module_path = compute_module_path(file, root_path=root)

            if decorator_type == "task":
                normal_tasks.append(TaskReference(str(file), func_name, module_path))
                continue

            if decorator_type == "scheduled_task":
                meta: Dict[str, Any] = {}
                try:
                    module = _load_module(module_path, str(file))
                    extracted = _extract_scheduled_metadata(module, func_name)
                    if extracted:
                        meta.update(extracted)
                except Exception as e:
                    logger.exception("[discover] Failed to load metadata for %s:%s", module_path or file, func_name)

                # Always enforce a task_name key (fallback to func name)
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
