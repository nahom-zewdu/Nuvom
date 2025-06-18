# nuvom/discovery/walker.py

"""
Provides utilities to recursively find Python files under a directory,
respecting include and exclude patterns, including .nuvomignore files
and default excludes like __pycache__, .git, etc.
"""

from pathlib import Path
from typing import List, Generator
import os

from nuvom.discovery.filters import PathspecMatcher
from nuvom.log import logger

DEFAULT_EXCLUDE_DIRS = {"__pycache__", ".venv", ".git", "migrations", ".pytest_cache"}
NUVOMIGNORE_FILE = ".nuvomignore"


def load_nuvomignore(root: Path) -> List[str]:
    """
    Load ignore patterns from a .nuvomignore file in the root directory.

    Args:
        root (Path): Root directory to look for .nuvomignore file.

    Returns:
        List[str]: List of ignore patterns, or empty if file not found.
    """
    ignore_path = root / NUVOMIGNORE_FILE
    if ignore_path.exists():
        try:
            with open(ignore_path) as f:
                patterns = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            logger.info(f"[walker] Loaded {len(patterns)} patterns from {NUVOMIGNORE_FILE}")
            return patterns
        except Exception as e:
            logger.warning(f"[walker] Failed to load {NUVOMIGNORE_FILE}: {e}")
            return []
    return []


def get_python_files(
    root: str,
    include: List[str],
    exclude: List[str]
) -> Generator[Path, None, None]:
    """
    Lazily yield Python files (.py) under `root` directory that match include patterns
    and do not match exclude patterns, using gitignore-style matching.

    Args:
        root (str): Root directory to search.
        include (List[str]): Glob patterns to include.
        exclude (List[str]): Glob patterns to exclude.

    Yields:
        Path: Full path of each matched Python file.
    """
    root_path = Path(root).resolve()
    ignore_patterns = load_nuvomignore(root_path)
    all_exclude_patterns = list(set(exclude + ignore_patterns))

    include_matcher = PathspecMatcher(include)
    exclude_matcher = PathspecMatcher(all_exclude_patterns)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out default excluded directories
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDE_DIRS]

        # Apply exclude patterns to directory paths (relative to root)
        dirnames[:] = [
            d for d in dirnames
            if not exclude_matcher.matches(str(Path(dirpath, d).relative_to(root_path).as_posix()) + "/")
        ]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            full_path = Path(dirpath) / filename
            relative_path = full_path.relative_to(root_path).as_posix()

            should_include = include_matcher.matches(relative_path) if include else True

            if should_include and not exclude_matcher.matches(relative_path):
                yield full_path
