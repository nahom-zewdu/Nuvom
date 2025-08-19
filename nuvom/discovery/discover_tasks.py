# nuvom/discovery/discover_tasks.py

"""
Core logic to scan a directory tree and discover all @task definitions.
Returns a list of TaskReference objects representing discovered tasks.
Supports filtering files via include and exclude glob patterns.
"""

from typing import List, Tuple
from pathlib import Path
from nuvom.discovery.walker import get_python_files
from nuvom.discovery.parser import find_task_defs
from nuvom.discovery.compute_path import compute_module_path
from nuvom.discovery.reference import TaskReference


def discover_tasks(
    root_path: str = ".",
    include: List[str] = [],
    exclude: List[str] = []
) -> Tuple[List[TaskReference], List[TaskReference]]:
    """
    Discover both @task and @scheduled_task in the codebase.

    Returns:
        normal_tasks: List[TaskReference] for @task
        scheduled_tasks: List[TaskReference] for @scheduled_task
    """
    normal_tasks: List[TaskReference] = []
    scheduled_tasks: List[TaskReference] = []

    files = get_python_files(root_path, include, exclude)
    root = Path(root_path).resolve()

    for file in files:
        task_defs = find_task_defs(file)  # [(func_name, decorator_type)]
        for func_name, decorator_type in task_defs:
            module_path = compute_module_path(file, root_path=root)
            ref = TaskReference(str(file), func_name, module_path)

            if decorator_type == "task":
                normal_tasks.append(ref)
            elif decorator_type == "scheduled_task":
                scheduled_tasks.append(ref)

    return normal_tasks, scheduled_tasks