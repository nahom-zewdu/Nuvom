# nuvom/discovery/parser.py

"""
Provides AST-based parsing utilities to statically detect function
definitions decorated with @task in Python source files.
"""

import ast
from pathlib import Path
from typing import List
from nuvom.log import logger


def find_task_defs(file_path: Path) -> List[str]:
    """
    Parse a Python source file and find all function names decorated with @task.

    Args:
        file_path (Path): Path to the Python source file.

    Returns:
        List[str]: List of function names decorated with @task.
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

    tasks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "task":
                    tasks.append(node.name)
                elif isinstance(decorator, ast.Attribute) and decorator.attr == "task":
                    tasks.append(node.name)
                elif isinstance(decorator, ast.Call):
                    # Check if decorator is a call to `task` or `x.task`
                    func = decorator.func
                    if (isinstance(func, ast.Name) and func.id == "task") or \
                       (isinstance(func, ast.Attribute) and func.attr == "task"):
                        tasks.append(node.name)
    return tasks
