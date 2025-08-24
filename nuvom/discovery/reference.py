# nuvom/discovery/reference.py

"""
Defines TaskReference, representing a discovered task's metadata and
provides dynamic loading of the task function from module or file.
"""

from typing import Optional


class TaskReference:
    """
    Represents metadata about a discovered task.

    Attributes:
        file_path (str): Absolute or relative path to the Python file.
        func_name (str): Name of the task function.
        module_name (Optional[str]): Python module path (dot notation).
    """

    def __init__(self, file_path: str, func_name: str, module_name: Optional[str] = None):
        self.file_path = file_path
        self.func_name = func_name
        self.module_name = module_name

    def __repr__(self):
        return f"<TaskReference {self.module_name or self.file_path}:{self.func_name}>"

    def load(self):
        """
        Dynamically load the task function.

        Returns:
            Callable: The task function.

        Raises:
            ImportError or AttributeError if loading fails.
        """
        import importlib.util
        import sys

        if self.module_name:
            module = __import__(self.module_name, fromlist=[""])
        else:
            spec = importlib.util.spec_from_file_location("dynamic_task_mod", self.file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules["dynamic_task_mod"] = module

        return getattr(module, self.func_name)
