# nuvom/result_backends/file_backend.py

import os
import json
from nuvom.result_backends.base import BaseResultBackend

DATA_DIR = os.path.expanduser("~/.nuvom/results")

class FileResultBackend(BaseResultBackend):
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)

    def _path(self, job_id, ext):
        return os.path.join(DATA_DIR, f"{job_id}.{ext}")

    def set_result(self, job_id, result):
        with open(self._path(job_id, "result"), "w") as f:
            json.dump(result, f)

    def get_result(self, job_id):
        path = self._path(job_id, "result")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)

    def set_error(self, job_id, error):
        with open(self._path(job_id, "error"), "w") as f:
            f.write(error)

    def get_error(self, job_id):
        path = self._path(job_id, "error")
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
