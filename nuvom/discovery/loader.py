# nuvom/discovery/loader.py

import importlib
import importlib.util
import sys
import hashlib
from types import ModuleType
from typing import Callable
from nuvom.discovery.reference import TaskReference


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
    Assigns a unique name to avoid sys.modules conflicts.
    """
    module_name = unique_module_name_from_path(path)
    spec = importlib.util.spec_from_file_location(module_name, path)

    if not spec or not spec.loader:
        raise ImportError(f"[loader] ❌ Cannot load spec from path: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"[loader] ❌ Failed to exec module {module_name}: {e}")

    return module


def load_task(ref: TaskReference) -> Callable:
    """
    Dynamically load the task function from a TaskReference.
    Tries to import using module name first, then falls back to file path.
    """
    module = None

    # Attempt module import if possible
    if ref.module_name:
        try:
            module = importlib.import_module(ref.module_name)
            print(f"[loader] ✅ Imported module: {ref.module_name}")
        except ImportError as e:
            print(f"[loader] ⚠ Failed to import '{ref.module_name}': {e}")
            print("[loader] ℹ Falling back to loading from file path...")

    # Fallback to dynamic path loading
    if module is None:
        module = load_module_from_path(ref.file_path)
        print(f"[loader] ✅ Loaded from path: {ref.file_path}")

    # Extract task
    if not hasattr(module, ref.func_name):
        raise AttributeError(f"[loader] ❌ Module '{module.__name__}' has no attribute '{ref.func_name}'")

    func = getattr(module, ref.func_name)

    if not callable(func):
        raise TypeError(f"[loader] ❌ '{ref.func_name}' in '{module.__name__}' is not callable")

    return func
