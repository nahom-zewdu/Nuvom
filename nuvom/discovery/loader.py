# nuvom/discovery/loader.py

"""
Dynamically loads modules and functions from file paths or module names.
Used to resolve and load task functions based on TaskReference data.
"""

import importlib
import importlib.util
import sys
import hashlib
from types import ModuleType
from typing import Callable

from nuvom.discovery.reference import TaskReference
from nuvom.log import get_logger

logger = get_logger()

def unique_module_name_from_path(path: str) -> str:
    """
    Generate a unique module name based on file path using a hash.
    Prevents module collision in sys.modules.
    """
    path_hash = hashlib.sha256(path.encode()).hexdigest()[:12]
    return f"nuvom_dynamic_{path_hash}"


def load_module_from_path(path: str) -> ModuleType:
    """
    Dynamically load a Python module from a file path.
    Args:
        path: Absolute file path to the .py source file.
    Returns:
        Loaded Python module object.
    Raises:
        ImportError: If module cannot be loaded or executed.
    """
    module_name = unique_module_name_from_path(path)
    spec = importlib.util.spec_from_file_location(module_name, path)

    if not spec or not spec.loader:
        raise ImportError(f"Cannot load spec from path: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Failed to exec module {module_name}: {e}")

    return module


def load_task(ref: TaskReference) -> Callable:
    """
    Dynamically load the task function from a TaskReference.
    Tries to import using module name first, then falls back to file path loading.
    Args:
        ref: A TaskReference object with module name and function name.
    Returns:
        Callable task function object.
    Raises:
        AttributeError: If the task function is not found in the module.
        TypeError: If the attribute is not a callable.
        ImportError: If module cannot be loaded.
    """
    module = None

    # Try standard module import
    if ref.module_name:
        try:
            module = importlib.import_module(ref.module_name)
            logger.info(f"[loader] ✅ Imported module: {ref.module_name}")
        except ImportError as e:
            logger.warning(f"[loader] ⚠ Failed to import '{ref.module_name}': {e}")
            logger.info("[loader] ℹ Falling back to loading from file path...")

    # Fallback to loading from path
    if module is None:
        module = load_module_from_path(ref.file_path)
        logger.info(f"[loader] ✅ Loaded from path: {ref.file_path}")

    # Extract function
    if not hasattr(module, ref.func_name):
        raise AttributeError(f"Module '{module.__name__}' has no attribute '{ref.func_name}'")

    func = getattr(module, ref.func_name)

    if not callable(func):
        raise TypeError(f"'{ref.func_name}' in '{module.__name__}' is not callable")

    return func
