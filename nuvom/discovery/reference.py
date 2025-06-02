# nuvom/discovery/reference.py

from typing import Optional


class TaskReference:
    def __init__(self, file_path: str, func_name: str, module_name: Optional[str] = None):
        self.file_path = file_path
        self.func_name = func_name
        self.module_name = module_name

    def __repr__(self):
        return f"<TaskReference {self.module_name or self.file_path}:{self.func_name}>"

    def load(self):
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
