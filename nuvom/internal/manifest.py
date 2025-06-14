from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Any
import json
import hashlib
import time

MANIFEST_VERSION = 1


@dataclass
class TaskReference:
    name: str                 # e.g., billing.send_email
    module_path: str          # e.g., myapp.tasks.email
    file_path: str            # absolute path
    function_name: str        # e.g., send_email
    file_hash: str            # sha256[:8] of file contents

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "TaskReference":
        return TaskReference(**data)


@dataclass
class ManifestV1:
    version: int
    discovered_at: str
    tasks: List[TaskReference]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "discovered_at": self.discovered_at,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @staticmethod
    def from_dict(data: dict) -> "ManifestV1":
        if data["version"] != MANIFEST_VERSION:
            raise ValueError(f"Incompatible manifest version: {data['version']}")
        tasks = [TaskReference.from_dict(t) for t in data["tasks"]]
        return ManifestV1(
            version=data["version"],
            discovered_at=data["discovered_at"],
            tasks=tasks
        )
