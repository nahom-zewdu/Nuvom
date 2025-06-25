# nuvom/result_store.py

"""
Central access point for result backend operations:
storing results, fetching them, and managing backend lifecycle.
"""

from nuvom.config import get_settings
from nuvom.result_backends.file_backend import FileResultBackend
from nuvom.result_backends.memory_backend import MemoryResultBackend

_backend = None


def get_backend():
    """
    Returns the active result backend, initializing it if necessary.
    """
    global _backend
    if _backend is not None:
        return _backend

    backend_name = get_settings().result_backend.lower()

    if backend_name == "file":
        _backend = FileResultBackend()
    elif backend_name == "memory":
        _backend = MemoryResultBackend()
    else:
        raise ValueError(f"Unsupported result backend: {backend_name}")

    return _backend


def reset_backend():
    """
    Resets the backend instance (for testing or config reload).
    """
    global _backend
    _backend = None


def set_result(job_id, func_name, result, *, args=None, kwargs=None, retries_left=None, attempts=None, created_at=None, completed_at=None):
    """
    Store the result for a given job ID, with full metadata.
    """
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
    """
    Retrieve the result for a given job ID.
    """
    return get_backend().get_result(job_id)



def set_error(job_id, func_name, error, *, args=None, kwargs=None, retries_left=None, attempts=None, created_at=None, completed_at=None):
    """
    Store an error for a given job ID, with full metadata.
    """
    get_backend().set_error(
        job_id=job_id,
        func_name=func_name,
        error=error,
        args=args,
        kwargs=kwargs,
        retries_left=retries_left,
        attempts=attempts,
        created_at=created_at,
        completed_at=completed_at
    )

def get_error(job_id):
    """
    Retrieve the error message for a given job ID.
    """
    return get_backend().get_error(job_id)
