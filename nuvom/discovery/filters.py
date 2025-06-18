# nuvom/discovery/filters.py

"""
Provides a wrapper around pathspec for gitignore-style pattern matching,
enabling inclusion/exclusion of files based on user-defined glob patterns.
"""

from typing import List
import pathspec


class PathspecMatcher:
    """
    Wrapper around pathspec to handle gitignore-style pattern matching.
    """
    def __init__(self, patterns: List[str]):
        clean_patterns = [p for p in patterns if p.strip()]
        self.spec = pathspec.PathSpec.from_lines("gitwildmatch", clean_patterns)

    def matches(self, path: str) -> bool:
        # path must be relative to root (or at least use POSIX separators)
        normalized_path = path.replace("\\", "/")
        return self.spec.match_file(normalized_path)
