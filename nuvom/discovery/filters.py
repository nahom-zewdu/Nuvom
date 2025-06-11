# nuvom/discovery/filters.py

import fnmatch
from typing import List

def match_patterns(path: str, patterns: List[str]) -> bool:
    """
    Return True if the given path matches *any* of the provided glob-style patterns.
    """
    normalized_path = path.replace("\\", "/")  # Ensure consistent path separators
    for pattern in patterns:
        normalized_pattern = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized_path, normalized_pattern):
            return True
    return False
