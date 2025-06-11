# nuvom/discovery/walker.py

from pathlib import Path
from typing import List, Generator
import os

from nuvom.discovery.filters import PathspecMatcher

DEFAULT_EXCLUDE_DIRS = {"__pycache__", ".venv", ".git", "migrations", ".pytest_cache"}
NUVOMIGNORE_FILE = ".nuvomignore"

def load_nuvomignore(root: Path) -> List[str]:
    ignore_path = root / NUVOMIGNORE_FILE
    if ignore_path.exists():
        with open(ignore_path) as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    return []

def get_python_files(
    root: str,
    include: List[str],
    exclude: List[str]
) -> Generator[Path, None, None]:
    """
    Lazily yields .py files under `root` that match include patterns and don't match exclude patterns.
    Supports .gitignore-style rules via pathspec.
    """
    
    root_path = Path(root).resolve()
    ignore_patterns = load_nuvomignore(root_path)
    all_exclude_patterns = list(set(exclude + ignore_patterns))

    include_matcher = PathspecMatcher(include)
    exclude_matcher = PathspecMatcher(all_exclude_patterns)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Always filter out default excluded dirs
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDE_DIRS]

        # Apply exclude patterns to full directory paths
        dirnames[:] = [
            d for d in dirnames
            if not exclude_matcher.matches(str(Path(dirpath, d).relative_to(root_path).as_posix())  + "/")
        ]
        
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            full_path = Path(dirpath) / filename
            relative_path = full_path.relative_to(root_path).as_posix()

            should_include = include_matcher.matches(relative_path) if include else True

            if should_include and not exclude_matcher.matches(relative_path):
                yield full_path
