# nuvom/discovery/compute_path.py
from pathlib import Path


def compute_module_path(file_path: Path) -> str:
    try:
        rel = file_path.relative_to(Path.cwd())
    except ValueError:
        rel = file_path
    return str(rel).replace("/", ".").replace("\\", ".").removesuffix(".py")
