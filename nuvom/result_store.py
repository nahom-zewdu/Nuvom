# nuvom/result_store.py

"""
Central access point for result-backend operations.

Key logic (v0.9+)
-----------------
1. Registry-based backend resolution (plugin or built-in)
2. Plugin autoload via `load_plugins()`
3. Special constructor case for SQLite (path required)
"""

from __future__ import annotations

import threading
from typing import Any

from nuvom.config import get_settings
from nuvom.log import get_logger
from nuvom.plugins.loader import load_plugins
from nuvom.plugins.registry import get_result_backend_cls

logger = get_logger()

_backend = None          # Singleton instance
_backend_lock = threading.Lock()  # Thread safety for lazy init


# --------------------------------------------------------------------------- #
# Backend factory
# --------------------------------------------------------------------------- #
def get_backend():
    """
    Return the active result backend (singleton).
    
    Resolution Order
    ----------------
    1. Load plugins (idempotent)
    2. Lookup backend class from registry
    3. Instantiate (sqlite receives path)
    """
    global _backend

    if _backend is not None:
        return _backend

    with _backend_lock:
        if _backend is not None:
            return _backend  # re-check inside lock

        settings = get_settings()
        load_plugins()  # ensure plugins are registered

        backend_name = settings.result_backend.strip().lower()
        backend_cls = get_result_backend_cls(backend_name)

        if backend_cls is None:
            raise ValueError(f"[ResultStore] Unsupported result backend: '{backend_name}'")

        try:
            if backend_name == "sqlite":
                _backend = backend_cls(settings.sqlite_db_path or ".nuvom/nuvom.db")
            else:
                _backend = backend_cls()  # type: ignore[call-arg]
        except Exception as e:
            logger.exception("[ResultStore] Failed to instantiate backend: %s", backend_name)
            raise RuntimeError(f"Backend instantiation failed: {e}") from e

        logger.info(
            "[ResultStore] Using '%s' backend (%s)",
            backend_name,
            backend_cls.__name__,
        )

        return _backend


def reset_backend() -> None:
    """Reset singleton instance (for tests or plugin reload)."""
    global _backend
    _backend = None


# --------------------------------------------------------------------------- #
# Convenience wrappers – preserve existing call‑site API
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


def get_result(job_id: str) -> Any:
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


def get_error(job_id: str) -> Any:
    return get_backend().get_error(job_id)
