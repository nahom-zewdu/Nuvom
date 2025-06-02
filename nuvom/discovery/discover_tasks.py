# nuvom/discovery/discover_tasks.py

from typing import List
from pathlib import Path
from nuvom.discovery.walker import get_python_files
from nuvom.discovery.parser import find_task_defs
from nuvom.discovery.loader import compute_module_path
from nuvom.discovery.reference import TaskReference


def discover_tasks(
    root_path: str = ".",
    include: List[str] = ["**/tasks.py"],
    exclude: List[str] = ["**/tests/**", "**/migrations/**"]
) -> List[TaskReference]:
    task_refs = []
    files = get_python_files(root_path, include, exclude)

    for file in files:
        task_names = find_task_defs(file)
        for name in task_names:
            module_path = compute_module_path(file)
            task_refs.append(TaskReference(str(file), name, module_path))

    return task_refs
