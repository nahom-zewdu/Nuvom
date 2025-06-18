# nuvom/result_backends/file_backend.py

import os

from nuvom.result_backends.base import BaseResultBackend
from nuvom.serialize import serialize, deserialize

class FileResultBackend(BaseResultBackend):
    def __init__(self):
        self.result_dir = "job_results"
        os.makedirs(self.result_dir, exist_ok=True)

    def _path(self, job_id):
        return os.path.join(self.result_dir, f"{job_id}.out")

    def _err_path(self, job_id):
        return os.path.join(self.result_dir, f"{job_id}.err")

    def set_result(self, job_id, result):
        os.makedirs(self.result_dir, exist_ok=True)  # Add here too
        with open(self._path(job_id), "wb") as f:
            f.write(serialize(result))

    def get_result(self, job_id):
        path = self._path(job_id)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return deserialize(f.read())

    def set_error(self, job_id, error):
        os.makedirs(self.result_dir, exist_ok=True)
        with open(self._err_path(job_id), "w") as f:
            f.write(str(error))

    def get_error(self, job_id):
        path = self._err_path(job_id)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return f.read()
