# nuvom/queue_backends/file_queue.py

import os
import uuid
import msgpack
from threading import Lock
from typing import List, Optional

from nuvom.job import Job
from nuvom.queue_backends.base import BaseJobQueue
from nuvom.serialize import serialize, deserialize

class FileJobQueue(BaseJobQueue):
    def __init__(self, directory="nuvom_queue"):
        self.dir = directory
        self.lock = Lock()
        os.makedirs(self.dir, exist_ok=True)

    def _job_path(self, job_id):
        return os.path.join(self.dir, f"{job_id}.msgpack")

    def enqueue(self, job: Job):
        job_id = job.id
        with open(self._job_path(job_id), "wb") as f:
            f.write(serialize(job.to_dict()))

    def dequeue(self, timeout=1) -> Optional[Job]:
        with self.lock:
            files = sorted(os.listdir(self.dir))
            for filename in files:
                try:
                    path = os.path.join(self.dir, filename)
                    with open(path, "rb") as f:
                        job_data = deserialize(f.read())
                        os.remove(path)
                        return Job.from_dict(job_data)
                except Exception:
                    continue
        return None

    def pop_batch(self, batch_size=1, timeout=1) -> List[Job]:
        jobs = []
        with self.lock:
            files = sorted(os.listdir(self.dir))[:batch_size]
            for filename in files:
                try:
                    path = os.path.join(self.dir, filename)
                    with open(path, "rb") as f:
                        job_data = deserialize(f.read())
                        os.remove(path)
                        jobs.append(Job.from_dict(job_data))
                except Exception:
                    continue
        return jobs

    def qsize(self) -> int:
        return len(os.listdir(self.dir))
