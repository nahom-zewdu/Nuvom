# nuvom/plugins/registry.py

"""
Central registry for all Nuvom plugins.

Provides:
    • register_queue_backend()
    • register_result_backend()
    • get_queue_backend_cls()
    • get_result_backend_cls()
"""

from typing import Dict, Type

# --------------------------------------------------------------------------- #
#  Internal storage
# --------------------------------------------------------------------------- #
_QUEUE_BACKENDS: Dict[str, Type] = {}
_RESULT_BACKENDS: Dict[str, Type] = {}


# --------------------------------------------------------------------------- #
#  Registration helpers
# --------------------------------------------------------------------------- #
def register_queue_backend(name: str, cls: Type, *, override: bool = False) -> None:
    """
    Register a queue backend under a short name (e.g. "sqlite", "redis").
    """
    _name = name.lower()
    if _name in _QUEUE_BACKENDS and not override:
        raise ValueError(f"Queue backend '{name}' already registered")
    _QUEUE_BACKENDS[_name] = cls


def register_result_backend(name: str, cls: Type, *, override: bool = False) -> None:
    """
    Register a result backend under a short name (e.g. "sqlite", "mongo").
    """
    _name = name.lower()
    if _name in _RESULT_BACKENDS and not override:
        raise ValueError(f"Result backend '{name}' already registered")
    _RESULT_BACKENDS[_name] = cls


# --------------------------------------------------------------------------- #
#  Lookup helpers
# --------------------------------------------------------------------------- #
def get_queue_backend_cls(name: str):
    return _QUEUE_BACKENDS.get(name.lower())


def get_result_backend_cls(name: str):
    return _RESULT_BACKENDS.get(name.lower())


# --------------------------------------------------------------------------- #
#  Built‑in registrations (Memory / File)
# --------------------------------------------------------------------------- #
# These imports are intentionally local to avoid circulars.
def _register_builtin_backends() -> None:
    """
    Register the built‑in queue & result backends so that plugins can
    safely override them later if desired.
    """
    from nuvom.queue_backends.memory_queue import MemoryJobQueue
    from nuvom.queue_backends.file_queue import FileJobQueue
    from nuvom.result_backends.memory_backend import MemoryResultBackend
    from nuvom.result_backends.file_backend import FileResultBackend
    from nuvom.result_backends.sqlite_backend import SQLiteResultBackend

    register_queue_backend("memory", MemoryJobQueue, override=True)
    register_queue_backend("file", FileJobQueue, override=True)

    register_result_backend("memory", MemoryResultBackend, override=True)
    register_result_backend("file", FileResultBackend, override=True)
    register_result_backend("sqlite", SQLiteResultBackend, override=True)


_register_builtin_backends()
