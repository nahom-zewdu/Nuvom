# nuvom/result_store.py

from nuvom.result_backends.file_backend import FileResultBackend

_backend = None

def get_backend():
    global _backend
    if _backend is None:
        # Later: switch based on config
        _backend = FileResultBackend()
    return _backend

def set_result(job_id, result):
    get_backend().set_result(job_id, result)

def get_result(job_id):
    return get_backend().get_result(job_id)

def set_error(job_id, error):
    get_backend().set_error(job_id, error)

def get_error(job_id):
    return get_backend().get_error(job_id)
