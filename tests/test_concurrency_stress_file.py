# Confirms that jobs aren't dropped or duplicated
# Ensures that file locks are adequately protecting critical regions
# Exposes race conditions or deletion clashes (os.remove during parallel reads)

import os
import shutil
import threading

from nuvom.job import Job
from nuvom.queue_backends.file_queue import FileJobQueue

TEST_QUEUE_DIR = "test_file_queue_concurrency"

def cleanup_dir():
    if os.path.exists(TEST_QUEUE_DIR):
        shutil.rmtree(TEST_QUEUE_DIR)

def enqueue_jobs(queue, count, thread_id):
    for i in range(count):
        job = Job(func_name=f"f-{thread_id}", args=(i,))
        queue.enqueue(job)

def dequeue_jobs(queue, count, results):
    for _ in range(count):
        job = queue.dequeue(timeout=2)
        if job:
            results.append((job.func_name, job.args[0]))

def test_concurrent_enqueue_dequeue_file_queue():
    cleanup_dir()
    queue = FileJobQueue(directory=TEST_QUEUE_DIR)
    num_jobs_per_thread = 5
    results = []

    # Start 2 enqueuers
    enqueue_threads = [
        threading.Thread(target=enqueue_jobs, args=(queue, num_jobs_per_thread, 1)),
        threading.Thread(target=enqueue_jobs, args=(queue, num_jobs_per_thread, 2)),
    ]

    # Start 1 dequeuer
    dequeue_thread = threading.Thread(target=dequeue_jobs, args=(queue, num_jobs_per_thread * 2, results))

    # Run threads
    for t in enqueue_threads:
        t.start()
    dequeue_thread.start()

    for t in enqueue_threads:
        t.join()
    dequeue_thread.join()

    # Assertions
    assert len(results) == num_jobs_per_thread * 2, f"Expected {num_jobs_per_thread*2} results, got {len(results)}"
    seen = set()
    for name, idx in results:
        key = (name, idx)
        assert key not in seen, f"Duplicate job: {key}"
        seen.add(key)

    cleanup_dir()
