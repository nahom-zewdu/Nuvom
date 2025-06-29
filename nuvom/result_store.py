# nuvom/result_store.py

"""
Central access point for result‑backend operations.

Key changes in v0.9
-------------------
1.  **Registry‑based resolution** – `get_backend()` now looks up the backend
    class in `nuvom.plugins.registry` *after* ensuring all plugins are loaded.
2.  **Plugin auto‑load** – calls `nuvom.plugins.loader.load_plugins()` once.
3.  **Built‑in backends registered via registry** – direct imports of
    `FileResultBackend`, `MemoryResultBackend`, … are no longer required here;
    they’re registered in `plugins.registry._register_builtin_backends()`.
"""

from __future__ import annotations

from typing import Any

from nuvom.config import get_settings
from nuvom.log import logger
from nuvom.plugins.loader import load_plugins
from nuvom.plugins.registry import get_result_backend_cls

_backend = None  # singleton instance


# --------------------------------------------------------------------------- #
#  Backend factory
# --------------------------------------------------------------------------- #
def get_backend():
    """
    Return the active result backend (singleton).

    Resolution order
    ----------------
    1. Load plugins (idempotent).
    2. Ask the **registry** for a backend class matching
       ``NUVOM_RESULT_BACKEND``.
    3. Instantiate it – passing ``sqlite_db_path`` fo SQLite.
    """
    global _backend
    if _backend is not None:
        return _backend

    settings = get_settings()
    load_plugins()  # ensure plugin modules have registered their backends

    backend_name = settings.result_backend.lower()
    backend_cls = get_result_backend_cls(backend_name)

    if backend_cls is None:  # still unknown → hard error
        raise ValueError(f"Unsupported result backend: '{backend_name}'")

    # Special‑case constructor kwargs (only SQLite for now)
    if backend_name == "sqlite":
        _backend = backend_cls(settings.sqlite_db_path or ".nuvom/nuvom.db")
    else:
        _backend = backend_cls()  # type: ignore[call-arg]

    logger.info("[ResultStore] Using %s backend (%s)", backend_name, backend_cls.__name__)
    return _backend


def reset_backend() -> None:
    """Clear the cached backend instance (primarily for tests)."""
    global _backend
    _backend = None


# --------------------------------------------------------------------------- #
#  Convenience wrappers – preserve existing call‑site API
# --------------------------------------------------------------------------- #
def set_result(
    job_id: str,
    func_name: str,
    result: Any,
    *,
    args=None,
    kwargs=None,
    retries_left=None,
    attempts=None,
    created_at=None,
    completed_at=None,
) -> None:
    get_backend().set_result(
        job_id=job_id,
        func_name=func_name,
        result=result,
        args=args,
        kwargs=kwargs,
        retries_left=retries_left,
        attempts=attempts,
        created_at=created_at,
        completed_at=completed_at,
    )


def get_result(job_id: str):
    return get_backend().get_result(job_id)


def set_error(
    job_id: str,
    func_name: str,
    error: Exception,
    *,
    args=None,
    kwargs=None,
    retries_left=None,
    attempts=None,
    created_at=None,
    completed_at=None,
) -> None:
    get_backend().set_error(
        job_id=job_id,
        func_name=func_name,
        error=error,
        args=args,
        kwargs=kwargs,
        retries_left=retries_left,
        attempts=attempts,
        created_at=created_at,
        completed_at=completed_at,
    )


def get_error(job_id: str):
    return get_backend().get_error(job_id)
