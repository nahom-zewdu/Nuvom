# nuvom/discovery/static_scanner.py

import ast
import fnmatch
from pathlib import Path
from typing import List, Optional


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
            module = importlib.import_module(self.module_name)
        else:
            spec = importlib.util.spec_from_file_location("dynamic_task_mod", self.file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules["dynamic_task_mod"] = module

        return getattr(module, self.func_name)


def match_patterns(path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def get_python_files(root: str, include: List[str], exclude: List[str]) -> List[Path]:
    all_py_files = Path(root).rglob("*.py")
    filtered = []
    for file in all_py_files:
        str_path = str(file)
        if match_patterns(str_path, include) and not match_patterns(str_path, exclude):
            filtered.append(file)
    return filtered


def find_task_defs(file_path: Path) -> List[str]:
    try:
        source = file_path.read_text()
    except Exception as e:
        print(f"[warn] Cannot read {file_path}: {e}")
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        print(f"[warn] Syntax error in {file_path}: {e}")
        return []

    tasks = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "task":
                    tasks.append(node.name)
                elif isinstance(decorator, ast.Attribute) and decorator.attr == "task":
                    tasks.append(node.name)

    return tasks


def compute_module_path(file_path: Path) -> str:
    try:
        rel = file_path.relative_to(Path.cwd())
    except ValueError:
        rel = file_path
    return str(rel).replace("/", ".").replace("\\", ".").removesuffix(".py")


def discover_tasks(
    root_path: str = ".",
    include: List[str] = ["**/tasks.py"],
    exclude: List[str] = ["**/tests/**", "**/migrations/**"]
) -> List[TaskReference]:
    include = include or ["**/tasks.py"]
    exclude = exclude or ["**/tests/**", "**/migrations/**"]

    task_refs = []
    files = get_python_files(root_path, include, exclude)

    for file in files:
        task_names = find_task_defs(file)
        for name in task_names:
            module_path = compute_module_path(file)
            task_refs.append(TaskReference(str(file), name, module_path))

    return task_refs
