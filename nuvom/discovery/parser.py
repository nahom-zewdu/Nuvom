# nuvom/discovery/parser.py

import ast
from pathlib import Path
from typing import List


def find_task_defs(file_path: Path) -> List[str]:
    try:
        source = file_path.read_text(encoding="utf-8")
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
