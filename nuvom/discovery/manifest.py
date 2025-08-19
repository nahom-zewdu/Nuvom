# nuvom/discovery/manifest.py

"""
Manifest management for discovered tasks
========================================

Persists the results of discovery into a single JSON file:
- tasks:            array of TaskReference
- scheduled_tasks:  array of ScheduledTaskReference (+ metadata)

Why keep metadata in the manifest?
----------------------------------
To allow the scheduler to reconstruct `ScheduledJob` instances *without importing
user code at runtime*. This reduces side effects and improves startup safety in
production workers.

Schema (v2.0)
-------------
{
  "version": "2.0",
  "tasks": [
    {"file_path": "...", "func_name": "add", "module_name": "tasks.jobs"}
  ],
  "scheduled_tasks": [
    {
      "file_path": "...",
      "func_name": "daily_cleanup",
      "module_name": "tasks.jobs",
      "metadata": {
        "schedule_type": "cron",
        "cron_expr": "0 0 * * *",
        "interval_secs": null,
        "run_at": null,
        "args": [],
        "kwargs": {},
        "enabled": true,
        "misfire_policy": "run_immediately",
        "concurrency_limit": 1,
        "queue_name": "default",
        "timezone": "UTC",
        "task_name": "daily_cleanup"
      }
    }
  ]
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from nuvom.discovery.reference import TaskReference, ScheduledTaskReference
from nuvom.log import get_logger

logger = get_logger()


class ManifestManager:
    """
    Handle read/write/diff operations for the discovery manifest.

    Attributes
    ----------
    path : Path
        Path to the manifest JSON file.
    tasks : List[TaskReference]
        Cached normal tasks.
    scheduled_tasks : List[ScheduledTaskReference]
        Cached scheduled tasks (with metadata).
    """

    VERSION = "2.0"
    DEFAULT_PATH = Path(".nuvom/manifest.json")

    def __init__(self, path: Optional[Path] = None):
        self.path = path or self.DEFAULT_PATH
        self.tasks: List[TaskReference] = []
        self.scheduled_tasks: List[ScheduledTaskReference] = []

    # ------------------------------------------------------------------ #
    # IO
    # ------------------------------------------------------------------ #
    def load(self) -> Dict[str, List[TaskReference]]:
        """
        Load manifest from disk.

        Returns
        -------
        dict
            {"tasks": List[TaskReference], "scheduled_tasks": List[ScheduledTaskReference]}

        Raises
        ------
        ValueError
            If manifest version mismatches expected version.
        """
        if not self.path.exists():
            logger.warning("[manifest] No manifest found at %s", self.path)
            self.tasks = []
            self.scheduled_tasks = []
            return {"tasks": [], "scheduled_tasks": []}

        with self.path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error("[manifest] Invalid JSON in manifest: %s", e)
                self.tasks, self.scheduled_tasks = [], []
                return {"tasks": [], "scheduled_tasks": []}

        if data.get("version") != self.VERSION:
            raise ValueError(f"[manifest] Version mismatch: {data.get('version')} != {self.VERSION}")

        self.tasks = [TaskReference(**item) for item in data.get("tasks", [])]

        self.scheduled_tasks = []
        for item in data.get("scheduled_tasks", []):
            # Backward/forward compatible: tolerate missing metadata key
            metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
            self.scheduled_tasks.append(
                ScheduledTaskReference(
                    file_path=item.get("file_path"),
                    func_name=item.get("func_name"),
                    module_name=item.get("module_name"),
                    metadata=metadata,
                )
            )

        return {"tasks": self.tasks, "scheduled_tasks": self.scheduled_tasks}

    def save(
        self,
        tasks: List[TaskReference],
        scheduled_tasks: List[ScheduledTaskReference],
    ) -> None:
        """
        Persist discovery results to disk.

        Parameters
        ----------
        tasks : List[TaskReference]
            Normal tasks to persist.
        scheduled_tasks : List[ScheduledTaskReference]
            Scheduled tasks to persist, including their metadata.
        """
        manifest = {
            "version": self.VERSION,
            "tasks": [self._serialize_task(t) for t in tasks],
            "scheduled_tasks": [self._serialize_scheduled_task(t) for t in scheduled_tasks],
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(
            "[manifest] Saved manifest: %d tasks, %d scheduled tasks",
            len(tasks),
            len(scheduled_tasks),
        )

    def get_all(self) -> Dict[str, List[TaskReference]]:
        """
        Return cached tasks.

        Returns
        -------
        dict
            {"tasks": [...], "scheduled_tasks": [...]}
        """
        return {"tasks": self.tasks, "scheduled_tasks": self.scheduled_tasks}

    # ------------------------------------------------------------------ #
    # Diff & Save
    # ------------------------------------------------------------------ #
    def diff_and_save(
        self,
        new_tasks: List[TaskReference],
        new_scheduled_tasks: List[ScheduledTaskReference],
    ) -> Dict[str, object]:
        """
        Compare new discovery results with the existing manifest, detect changes,
        and save if needed.

        Returns
        -------
        dict
            {
              "tasks": {
                "added": [...], "removed": [...], "modified": [...]
              },
              "scheduled_tasks": {
                "added": [...], "removed": [...], "modified": [...]
              },
              "saved": bool
            }
        """
        old = self.load()

        def to_map_tasks(lst: List[TaskReference]) -> Dict[str, TaskReference]:
            return {self._task_key(t): t for t in lst}

        def to_map_sched(lst: List[ScheduledTaskReference]) -> Dict[str, ScheduledTaskReference]:
            return {self._task_key(t): t for t in lst}

        results: Dict[str, Any] = {}
        changed = False

        # Normal tasks
        old_map = to_map_tasks(old["tasks"])
        new_map = to_map_tasks(new_tasks)
        t_added = [t for k, t in new_map.items() if k not in old_map]
        t_removed = [t for k, t in old_map.items() if k not in new_map]
        t_modified = [
            new_map[k] for k in new_map.keys() & old_map.keys()
            if self._task_changed(old_map[k], new_map[k])
        ]
        if t_added or t_removed or t_modified:
            changed = True

        results["tasks"] = {"added": t_added, "removed": t_removed, "modified": t_modified}

        # Scheduled tasks
        old_map_s = to_map_sched(old["scheduled_tasks"])
        new_map_s = to_map_sched(new_scheduled_tasks)
        s_added = [t for k, t in new_map_s.items() if k not in old_map_s]
        s_removed = [t for k, t in old_map_s.items() if k not in new_map_s]
        s_modified = [
            new_map_s[k] for k in new_map_s.keys() & old_map_s.keys()
            if self._scheduled_task_changed(old_map_s[k], new_map_s[k])
        ]
        if s_added or s_removed or s_modified:
            changed = True

        results["scheduled_tasks"] = {"added": s_added, "removed": s_removed, "modified": s_modified}

        if changed:
            self.save(new_tasks, new_scheduled_tasks)
            logger.info("[manifest] Changes detected and saved.")
        else:
            logger.info("[manifest] No changes detected.")

        return {**results, "saved": changed}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _serialize_task(self, task: TaskReference) -> dict:
        """Serialize TaskReference for JSON output."""
        return {
            "file_path": task.file_path,
            "func_name": task.func_name,
            "module_name": task.module_name,
        }

    def _serialize_scheduled_task(self, task: ScheduledTaskReference) -> dict:
        """Serialize ScheduledTaskReference for JSON output (including metadata)."""
        return {
            "file_path": task.file_path,
            "func_name": task.func_name,
            "module_name": task.module_name,
            "metadata": task.metadata or {},
        }

    def _task_key(self, task: TaskReference) -> str:
        """
        A stable identity key for both normal and scheduled tasks.
        Using module:function (fallback to file path if module missing).
        """
        return f"{task.module_name or task.file_path}:{task.func_name}"

    def _task_changed(self, old: TaskReference, new: TaskReference) -> bool:
        """
        A normal task is considered modified if its file or module location changed.
        """
        return (old.file_path != new.file_path) or (old.module_name != new.module_name)

    def _scheduled_task_changed(self, old: ScheduledTaskReference, new: ScheduledTaskReference) -> bool:
        """
        A scheduled task is considered modified if location changed *or* metadata changed.
        """
        if self._task_changed(old, new):
            return True

        # Compare metadata content (shallow, JSON-serializable)
        old_meta = old.metadata or {}
        new_meta = new.metadata or {}
        return old_meta != new_meta
