# nuvom/discovery/walker.py

from pathlib import Path
from typing import List
import os
from nuvom.discovery.filters import match_patterns

DEFAULT_EXCLUDE_DIRS = {"**/__pycache__/**", "**/.venv/**", "**/.git/**", "**/.tests/**" , "**/migrations/**", "**/.pytest_cache/**"}
NUVOMIGNORE_FILE = ".nuvomignore"

def load_nuvomignore(root: Path) -> List[str]:
    ignore_path = root / NUVOMIGNORE_FILE
    if ignore_path.exists():
        with open(ignore_path) as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            return lines
    return []

def get_python_files(root: str, include: List[str], exclude: List[str]) -> List[Path]:
    """
    Recursively returns all .py files under `root` that match include patterns and don't match exclude patterns.
    Default ignores: __pycache__, .venv, .git, .tests, migrations.
    """
    
    root_path = Path(root).resolve()
    exclude_dirs = DEFAULT_EXCLUDE_DIRS.copy()
    ignore_patterns = load_nuvomignore(root_path)
    exclude += ignore_patterns

    files = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not match_patterns(os.path.join(dirpath, d), exclude)]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            full_path = os.path.join(dirpath, filename)
            if match_patterns(full_path, include) and not match_patterns(full_path, exclude):
                files.append(Path(full_path))

    return files
