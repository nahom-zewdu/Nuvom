# nuvom/result_store.py

from nuvom.config import get_settings
from nuvom.result_backends.file_backend import FileResultBackend
from nuvom.result_backends.memory_backend import MemoryResultBackend 

_backend = None

def get_backend():
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
    global _backend
    _backend = None

def set_result(job_id, result):
    get_backend().set_result(job_id, result)

def get_result(job_id):
    return get_backend().get_result(job_id)

def set_error(job_id, error):
    get_backend().set_error(job_id, error)

def get_error(job_id):
    return get_backend().get_error(job_id)
