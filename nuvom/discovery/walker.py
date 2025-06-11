# nuvom/discovery/walker.py

import os
from pathlib import Path
from typing import List
from nuvom.discovery.filters import match_patterns

DEFAULT_EXCLUDE_DIRS = ["**/__pycache__/**", "**/.venv/**", "**/.git/**", "**/.tests/**" , "**/migrations/**"]

def get_python_files(root: str, include: List[str], exclude: List[str]) -> List[Path]:
    """
    Recursively returns all .py files under `root` that match include patterns and don't match exclude patterns.
    Default ignores: __pycache__, .venv, .git, .tests, migrations.
    """

    exclude += DEFAULT_EXCLUDE_DIRS
    matched_files = []
    root_path = Path(root).resolve()

    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = Path(dirpath).relative_to(root_path)
        str_dir = str(rel_dir).replace("\\", "/")
        # Exclude dirs
        if match_patterns(str_dir + "/", exclude):
            dirnames[:] = []  # Prevent walking into this directory
            continue

        for fname in filenames:
            if not fname.endswith(".py"):
                continue

            fpath = Path(dirpath) / fname
            str_path = str(fpath.relative_to(root_path)).replace("\\", "/")

            if match_patterns(str_path, include) and not match_patterns(str_path, exclude):
                matched_files.append(fpath)

    return matched_files
