# nuvom/discovery/walker.py

from pathlib import Path
from typing import List
from nuvom.discovery.filters import match_patterns


def get_python_files(root: str, include: List[str], exclude: List[str]) -> List[Path]:
    all_py_files = Path(root).rglob("*.py")
    filtered = []
    for file in all_py_files:
        str_path = str(file)
        if match_patterns(str_path, include) and not match_patterns(str_path, exclude):
            filtered.append(file)
    return filtered
