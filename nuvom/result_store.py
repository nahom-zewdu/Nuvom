# nuvom/result_store.py

"""
Central access point for result backend operations:
storing results, fetching them, and managing backend lifecycle.
"""

from nuvom.config import get_settings
from nuvom.result_backends.file_backend import FileResultBackend
from nuvom.result_backends.memory_backend import MemoryResultBackend
from nuvom.result_backends.sqlite_backend import SQLiteResultBackend  # NEW ✅

_backend = None


def get_backend():
    """
    Return the active result backend (singleton).  
    Lazily instantiates the backend based on ``NUVOM_RESULT_BACKEND``.
    """
    global _backend
    if _backend is not None:
        return _backend

    settings = get_settings()
    backend_name = settings.result_backend.lower()

    if backend_name == "file":
        _backend = FileResultBackend()
    elif backend_name == "memory":
        _backend = MemoryResultBackend()
    elif backend_name == "sqlite":
        _backend = SQLiteResultBackend(settings.sqlite_db_path or ".nuvom/nuvom.db")
    else:
        raise ValueError(f"Unsupported result backend: {backend_name}")

    return _backend


# ---------------------------------------------------------------------------#
# Convenience wrappers that push full metadata into whichever backend is set #
# ---------------------------------------------------------------------------#
def reset_backend():
    """Reset the cached backend instance (used by tests)."""
    global _backend
    _backend = None


def set_result(
    job_id,
    func_name,
    result,
    *,
    args=None,
    kwargs=None,
    retries_left=None,
    attempts=None,
    created_at=None,
    completed_at=None,
):
    """Persist a successful job result with full metadata."""
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


def get_result(job_id):
    """Retrieve only the deserialized result value (or ``None``)."""
    return get_backend().get_result(job_id)


def set_error(
    job_id,
    func_name,
    error,
    *,
    args=None,
    kwargs=None,
    retries_left=None,
    attempts=None,
    created_at=None,
    completed_at=None,
):
    """Persist a failed job’s error with traceback and metadata."""
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


def get_error(job_id):
    """Return the stored error message (or ``None``)."""
    return get_backend().get_error(job_id)
