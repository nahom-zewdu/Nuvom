# nuvom/result_store.py

from typing import Any, Dict

_RESULT_STORE: Dict[str, Any] = {}
_ERROR_STORE: Dict[str, str] = {}

def store_result(job_id: str, result: Any):
    _RESULT_STORE[job_id] = result

def get_result(job_id: str) -> Any:
    return _RESULT_STORE.get(job_id)

def store_error(job_id: str, error: str):
    _ERROR_STORE[job_id] = error

def get_error(job_id: str) -> str:
    return _ERROR_STORE.get(job_id)
