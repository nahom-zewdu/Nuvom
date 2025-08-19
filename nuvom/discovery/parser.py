# nuvom/discovery/parser.py

"""
Provides AST-based parsing utilities to statically detect function
definitions decorated with @task and @scheduled_task in Python source files.
"""

import ast
from pathlib import Path
from typing import List, Tuple, Optional
from nuvom.log import get_logger

logger = get_logger()

def find_task_defs(file_path: Path) -> List[Tuple[str, Optional[str]]]:
    """
    Parse a Python file and find all function names decorated with
    @task or @scheduled_task.

    Returns:
        List of tuples: (func_name, decorator_type)
        decorator_type is either "task" or "scheduled_task"
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"[parser] Cannot read {file_path}: {e}")
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        logger.warning(f"[parser] Syntax error in {file_path}: {e}")
        return []

    results: List[Tuple[str, Optional[str]]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                name = None
                if isinstance(decorator, ast.Name):
                    if decorator.id == "task":
                        name = "task"
                    elif decorator.id == "scheduled_task":
                        name = "scheduled_task"
                elif isinstance(decorator, ast.Attribute):
                    if decorator.attr == "task":
                        name = "task"
                    elif decorator.attr == "scheduled_task":
                        name = "scheduled_task"
                elif isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Name):
                        if func.id == "task":
                            name = "task"
                        elif func.id == "scheduled_task":
                            name = "scheduled_task"
                    elif isinstance(func, ast.Attribute):
                        if func.attr == "task":
                            name = "task"
                        elif func.attr == "scheduled_task":
                            name = "scheduled_task"

                if name:
                    results.append((node.name, name))

    return results