# nuvom/discovery/manifest.py

"""
Manages the manifest file storing discovered task metadata.
Supports reading, writing, and diffing manifest contents
to track changes in discovered tasks.
"""

import json
from pathlib import Path
from typing import List, Optional
from nuvom.discovery.reference import TaskReference
from nuvom.log import logger


class ManifestManager:
    """
    Handles read/write operations for the manifest file that stores
    discovered tasks' metadata.

    Attributes:
        path (Path): Path to the manifest JSON file.
        tasks (List[TaskReference]): Cached list of loaded tasks.
    """

    VERSION = "1.0"
    DEFAULT_PATH = Path(".nuvom/manifest.json")

    def __init__(self, path: Optional[Path] = None):
        self.path = path or self.DEFAULT_PATH
        self.tasks: List[TaskReference] = []

    def load(self) -> List[TaskReference]:
        """
        Load manifest tasks from disk.

        Returns:
            List[TaskReference]: List of tasks from manifest.

        Logs warnings if file is missing or JSON is invalid.
        Raises:
            ValueError: If manifest version mismatches expected version.
        """
        if not self.path.exists():
            logger.warning(f"[manifest] No manifest found at {self.path}")
            self.tasks = []
            return []

        with self.path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"[manifest] Invalid JSON in manifest: {e}")
                self.tasks = []
                return []

        if data.get("version") != self.VERSION:
            raise ValueError(f"[manifest] Version mismatch: {data.get('version')} != {self.VERSION}")

        self.tasks = [TaskReference(**item) for item in data.get("tasks", [])]
        return self.tasks

    def save(self, tasks: List[TaskReference]):
        """
        Save a list of TaskReferences to the manifest file.

        Args:
            tasks (List[TaskReference]): Tasks to save.
        """
        manifest = {
            "version": self.VERSION,
            "tasks": [self._serialize_task(t) for t in tasks],
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"[manifest] Saved manifest with {len(tasks)} tasks to {self.path}")

    def _serialize_task(self, task: TaskReference) -> dict:
        """
        Serialize TaskReference to dictionary for JSON output.

        Args:
            task (TaskReference): Task to serialize.

        Returns:
            dict: Serialized task data.
        """
        return {
            "file_path": task.file_path,
            "func_name": task.func_name,
            "module_name": task.module_name,
        }

    def get_all(self) -> List[TaskReference]:
        """
        Get cached list of loaded tasks.

        Returns:
            List[TaskReference]: Cached tasks.
        """
        return self.tasks

    def diff_and_save(self, new_tasks: List[TaskReference]) -> dict:
        """
        Compare new task list with existing manifest tasks,
        detect added, removed, and modified tasks,
        and save new manifest if changes exist.

        Args:
            new_tasks (List[TaskReference]): Newly discovered tasks.

        Returns:
            dict: Summary of changes with keys 'added', 'removed',
                  'modified', and 'saved' (bool).
        """
        old_set = {self._task_key(t): t for t in self.load()}
        new_set = {self._task_key(t): t for t in new_tasks}

        added = [t for k, t in new_set.items() if k not in old_set]
        removed = [t for k, t in old_set.items() if k not in new_set]
        modified = [
            new_set[k] for k in new_set.keys() & old_set.keys()
            if self._task_changed(old_set[k], new_set[k])
        ]

        changed = bool(added or removed or modified)
        if changed:
            self.save(new_tasks)
            logger.info(
                f"[manifest] Manifest changed: +{len(added)} added, "
                f"-{len(removed)} removed, ~{len(modified)} modified"
            )
        else:
            logger.info("[manifest] No manifest changes detected.")

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "saved": changed,
        }

    def _task_key(self, task: TaskReference) -> str:
        """
        Compute a unique key for a task used in comparisons.

        Args:
            task (TaskReference): Task to compute key for.

        Returns:
            str: Unique string key.
        """
        return f"{task.module_name or task.file_path}:{task.func_name}"

    def _task_changed(self, old: TaskReference, new: TaskReference) -> bool:
        """
        Determine if two TaskReferences differ in file path or module.

        Args:
            old (TaskReference): Old task data.
            new (TaskReference): New task data.

        Returns:
            bool: True if changed, False otherwise.
        """
        return (old.file_path != new.file_path or old.module_name != new.module_name)
