# nuvom/discovery/compute_path.py

"""
Utility function to compute a Python module path string from a file path,
relative to a root directory. Converts file path to dot notation and
removes the `.py` suffix for proper module import paths.
"""

from pathlib import Path

def compute_module_path(file_path: Path, root_path: Path) -> str:
    try:
        rel = file_path.relative_to(root_path)
    except ValueError:
        rel = file_path
    return str(rel).replace("/", ".").replace("\\", ".").removesuffix(".py")
