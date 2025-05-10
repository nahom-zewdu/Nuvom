# Maintains the job buffer (FIFO or priority)
# Supports optional batch pulls
# Backpressure handling if needed

import queue
import threading

from nuvom.serialize import get_serializer
from nuvom.job import Job  # make sure this path is correct

_GLOBAL_QUEUE = None
_GLOBAL_LOCK = threading.Lock()


class JobQueue:
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


def get_global_queue():
    global _GLOBAL_QUEUE
    with _GLOBAL_LOCK:
        if _GLOBAL_QUEUE is None:
            _GLOBAL_QUEUE = JobQueue()
        return _GLOBAL_QUEUE
