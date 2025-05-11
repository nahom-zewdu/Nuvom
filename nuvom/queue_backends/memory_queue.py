# nuvom/queue_backends/memory_queue.py

import queue
import threading

from nuvom.serialize import get_serializer
from nuvom.job import Job  # make sure this path is correct

class MemoryJobQueue:
    def __init__(self, maxsize=0):
        self.q = queue.Queue(maxsize=maxsize)
        self.lock = threading.Lock()
        self.serializer = get_serializer()

    def enqueue(self, job: Job):
        serialized = self.serializer.serialize(job.to_dict())
        self.q.put(serialized)

    def dequeue(self, timeout=1) -> Job | None:
        try:
            data = self.q.get(timeout=timeout)
            job_dict = self.serializer.deserialize(data)
            return Job.from_dict(job_dict)
        except queue.Empty:
            return None

    def pop_batch(self, batch_size=1, timeout=1):
        batch = []
        with self.lock:
            for _ in range(batch_size):
                try:
                    data = self.q.get(timeout=timeout)
                    job_dict = self.serializer.deserialize(data)
                    batch.append(Job.from_dict(job_dict))
                except queue.Empty:
                    break
        return batch

    def qsize(self):
        return self.q.qsize()