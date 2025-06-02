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
