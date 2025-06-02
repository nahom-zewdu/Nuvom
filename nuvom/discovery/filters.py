# nuvom/discovery/filters.py

import fnmatch
from typing import List


def match_patterns(path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)
