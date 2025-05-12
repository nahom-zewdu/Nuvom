import threading
from nuvom.queue_backends.memory_queue import MemoryJobQueue
from nuvom.job import Job

def enqueue_jobs(q, count, func_name="stress"):
    for i in range(count):
        job = Job(func_name=func_name, args=(i,))
        q.enqueue(job)

def dequeue_jobs(q, count, results):
    for _ in range(count):
        job = q.dequeue(timeout=2)
        if job:
            results.append(job.args[0])

def test_concurrent_enqueue_dequeue():
    q = MemoryJobQueue()
    num_jobs = 1000

    enqueue_thread1 = threading.Thread(target=enqueue_jobs, args=(q, num_jobs//2))
    enqueue_thread2 = threading.Thread(target=enqueue_jobs, args=(q, num_jobs//2))
    results = []
    dequeue_thread = threading.Thread(target=dequeue_jobs, args=(q, num_jobs, results))

    enqueue_thread1.start()
    enqueue_thread2.start()
    dequeue_thread.start()

    enqueue_thread1.join()
    enqueue_thread2.join()
    dequeue_thread.join()

    assert len(results) == num_jobs
    assert list(set(sorted(results))) == list(range(num_jobs)) or len(set(results)) == num_jobs//2
