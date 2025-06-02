# nuvom/discovery/manifest.py

import json
from pathlib import Path
from typing import List, Optional
from nuvom.discovery.reference import TaskReference


class ManifestManager:
    """
    Handles read/write of the manifest file storing discovered tasks.
    """
    VERSION = "1.0"
    DEFAULT_PATH = Path(".nuvom/manifest.json")

    def __init__(self, path: Optional[Path] = None):
        self.path = path or self.DEFAULT_PATH
        self.tasks: List[TaskReference] = []

    def load(self) -> List[TaskReference]:
        if not self.path.exists():
            print(f"[manifest] No manifest found at {self.path}")
            self.tasks = []
            return []

        with self.path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[manifest] Invalid JSON: {e}")
                self.tasks = []
                return []

        if data.get("version") != self.VERSION:
            raise ValueError(f"[manifest] Version mismatch: {data.get('version')} != {self.VERSION}")

        self.tasks = [TaskReference(**item) for item in data.get("tasks", [])]
        return self.tasks

    def save(self, tasks: List[TaskReference]):
        manifest = {
            "version": self.VERSION,
            "tasks": [self._serialize_task(t) for t in tasks]
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def _serialize_task(self, task: TaskReference) -> dict:
        return {
            "file_path": task.file_path,
            "func_name": task.func_name,
            "module_name": task.module_name,
        }

    def get_all(self) -> List[TaskReference]:
        return self.tasks
    
    def diff_and_save(self, new_tasks: List[TaskReference]) -> dict:
        old_set = {self._task_key(t): t for t in self.load()}
        new_set = {self._task_key(t): t for t in new_tasks}

        added = [t for k, t in new_set.items() if k not in old_set]
        removed = [t for k, t in old_set.items() if k not in new_set]
        modified = [
            new_set[k] for k in new_set.keys() & old_set.keys()
            if self._task_changed(old_set[k], new_set[k])
        ]

        changed = added or removed or modified
        if changed:
            self.save(new_tasks)

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "saved": bool(changed)
        }

    def _task_key(self, task: TaskReference) -> str:
        return f"{task.module_name or task.file_path}:{task.func_name}"

    def _task_changed(self, old: TaskReference, new: TaskReference) -> bool:
        return (old.file_path != new.file_path or old.module_name != new.module_name)

