# nuvom/backends/memory_backend.py

from nuvom.result_backends.base import BaseResultBackend

class MemoryResultBackend(BaseResultBackend):
    def __init__(self):
        self.results = {}
        self.errors = {}

    def set_result(self, job_id, result):
        self.results[job_id] = result

    def get_result(self, job_id):
        return self.results.get(job_id)

    def set_error(self, job_id, error):
        self.errors[job_id] = error

    def get_error(self, job_id):
        return self.errors.get(job_id)
