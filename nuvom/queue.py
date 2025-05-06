# Maintains the job buffer (FIFO or priority)
# Supports optional batch pulls
# Backpressure handling if needed

import queue
import threading

# Global default queue (used by @task.delay)
_GLOBAL_QUEUE = None
_GLOBAL_LOCK = threading.Lock()


class JobQueue:
    def __init__(self, maxsize=0):
        self.q = queue.Queue(maxsize=maxsize)  # 0 = infinite size
        self.lock = threading.Lock()  # for batch pop

    def enqueue(self, job):
        self.q.put(job)

    def dequeue(self, timeout=1):
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def pop_batch(self, batch_size=1, timeout=1):
        batch = []
        with self.lock:
            for _ in range(batch_size):
                try:
                    job = self.q.get(timeout=timeout)
                    batch.append(job)
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
