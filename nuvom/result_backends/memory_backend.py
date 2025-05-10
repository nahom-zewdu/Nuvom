# nuvom/backends/memory_backend.py

from nuvom.serialize import serialize, deserialize
from nuvom.result_backends.base import BaseResultBackend

class MemoryResultBackend(BaseResultBackend):
    def __init__(self):
        self._results = {}
        self._errors = {}

    def set_result(self, job_id, result):
        self._results[job_id] = serialize(result)

    def get_result(self, job_id):
        raw = self._results.get(job_id)
        return deserialize(raw) if raw else None

    def set_error(self, job_id, error):
        self._errors[job_id] = str(error)

    def get_error(self, job_id):
        return self._errors.get(job_id)
