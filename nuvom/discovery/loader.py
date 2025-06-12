# nuvom/discovery/loader.py

import importlib.util
import importlib
import sys
from types import ModuleType
from typing import Callable
from nuvom.discovery.reference import TaskReference


def load_module_from_path(path: str, module_name: str = "dynamic_task_mod") -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load module from path: {path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_task(ref: TaskReference) -> Callable:
    """
    Dynamically load the task function from a TaskReference.
    """
    if ref.module_name:
        try:
            module = importlib.import_module(ref.module_name)
        except ImportError as e:
            raise ImportError(f"Failed to import module '{ref.module_name}': {e}")
    else:
        module = load_module_from_path(ref.file_path)

    if not hasattr(module, ref.func_name):
        raise AttributeError(f"Module '{module.__name__}' has no attribute '{ref.func_name}'")

    func = getattr(module, ref.func_name)
    if not callable(func):
        raise TypeError(f"'{ref.func_name}' in '{module.__name__}' is not callable")

    return func
