# nuvom/discovery/manifest.py

"""
Manages the manifest file storing discovered task metadata.
Now supports both normal tasks (@task) and scheduled tasks (@scheduled_task).
Tracks changes separately for each category and persists them
in a single manifest file.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict
from nuvom.discovery.reference import TaskReference
from nuvom.log import get_logger

logger = get_logger()

class ManifestManager:
    """
    Handles read/write operations for the manifest file that stores
    discovered tasks' metadata.

    Manifest Schema (v2.0):
    {
        "version": "2.0",
        "tasks": [...],
        "scheduled_tasks": [...]
    }

    Attributes
    ----------
    path : Path
        Path to the manifest JSON file.
    tasks : List[TaskReference]
        Cached list of normal tasks.
    scheduled_tasks : List[TaskReference]
        Cached list of scheduled tasks.
    """

    VERSION = "2.0"
    DEFAULT_PATH = Path(".nuvom/manifest.json")

    def __init__(self, path: Optional[Path] = None):
        self.path = path or self.DEFAULT_PATH
        self.tasks: List[TaskReference] = []
        self.scheduled_tasks: List[TaskReference] = []

    def load(self) -> Dict[str, List[TaskReference]]:
        """
        Load manifest tasks from disk.

        Returns
        -------
        dict
            {"tasks": List[TaskReference], "scheduled_tasks": List[TaskReference]}

        Raises
        ------
        ValueError
            If manifest version mismatches expected version.
        """
        if not self.path.exists():
            logger.warning(f"[manifest] No manifest found at {self.path}")
            self.tasks = []
            self.scheduled_tasks = []
            return {"tasks": [], "scheduled_tasks": []}

        with self.path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"[manifest] Invalid JSON in manifest: {e}")
                self.tasks, self.scheduled_tasks = [], []
                return {"tasks": [], "scheduled_tasks": []}

        if data.get("version") != self.VERSION:
            raise ValueError(
                f"[manifest] Version mismatch: {data.get('version')} != {self.VERSION}"
            )

        self.tasks = [TaskReference(**item) for item in data.get("tasks", [])]
        self.scheduled_tasks = [
            TaskReference(**item) for item in data.get("scheduled_tasks", [])
        ]
        return {"tasks": self.tasks, "scheduled_tasks": self.scheduled_tasks}

    def save(
        self, tasks: List[TaskReference], scheduled_tasks: List[TaskReference]
    ) -> None:
        """
        Save both normal and scheduled tasks to the manifest file.

        Parameters
        ----------
        tasks : List[TaskReference]
            Normal tasks to persist.
        scheduled_tasks : List[TaskReference]
            Scheduled tasks to persist.
        """
        manifest = {
            "version": self.VERSION,
            "tasks": [self._serialize_task(t) for t in tasks],
            "scheduled_tasks": [self._serialize_task(t) for t in scheduled_tasks],
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(
            f"[manifest] Saved manifest: "
            f"{len(tasks)} tasks, {len(scheduled_tasks)} scheduled tasks"
        )

    def get_all(self) -> Dict[str, List[TaskReference]]:
        """
        Get cached tasks.

        Returns
        -------
        dict
            {"tasks": [...], "scheduled_tasks": [...]}
        """
        return {"tasks": self.tasks, "scheduled_tasks": self.scheduled_tasks}

    def diff_and_save(
        self,
        new_tasks: List[TaskReference],
        new_scheduled_tasks: List[TaskReference],
    ) -> Dict[str, object]:
        """
        Compare new discovery results with existing manifest contents,
        detect added/removed/modified tasks (for both categories),
        and save manifest if changes exist.

        Returns
        -------
        dict
            {
                "added": {"tasks": [...], "scheduled_tasks": [...]},
                "removed": {...},
                "modified": {...},
                "saved": bool
            }
        """
        old = self.load()

        def to_map(lst: List[TaskReference]) -> Dict[str, TaskReference]:
            return {self._task_key(t): t for t in lst}

        results = {}
        changed = False

        for category, old_list, new_list in [
            ("tasks", old["tasks"], new_tasks),
            ("scheduled_tasks", old["scheduled_tasks"], new_scheduled_tasks),
        ]:
            old_map = to_map(old_list)
            new_map = to_map(new_list)

            added = [t for k, t in new_map.items() if k not in old_map]
            removed = [t for k, t in old_map.items() if k not in new_map]
            modified = [
                new_map[k] for k in new_map.keys() & old_map.keys()
                if self._task_changed(old_map[k], new_map[k])
            ]

            if added or removed or modified:
                changed = True

            results[category] = {
                "added": added,
                "removed": removed,
                "modified": modified,
            }

        if changed:
            self.save(new_tasks, new_scheduled_tasks)
            logger.info("[manifest] Changes detected and saved.")
        else:
            logger.info("[manifest] No changes detected.")

        return {**results, "saved": changed}

    def _serialize_task(self, task: TaskReference) -> dict:
        """Serialize TaskReference for JSON output."""
        return {
            "file_path": task.file_path,
            "func_name": task.func_name,
            "module_name": task.module_name,
        }

    def _task_key(self, task: TaskReference) -> str:
        return f"{task.module_name or task.file_path}:{task.func_name}"

    def _task_changed(self, old: TaskReference, new: TaskReference) -> bool:
        return (old.file_path != new.file_path or old.module_name != new.module_name)
