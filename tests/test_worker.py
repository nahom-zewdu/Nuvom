# tests/test_worker.py

from nuvom.task import task
from nuvom.queue import get_global_queue
from nuvom.result_store import get_result
from nuvom.worker import start_worker_pool
import threading
import time

@task
def multiply(a, b):
    return a * b

def test_worker_executes_job():
    job = multiply.delay(4, 5)

    # Run a single worker thread in the background
    thread = threading.Thread(target=start_worker_pool, daemon=True)
    thread.start()

    time.sleep(2)  # Wait for job to be picked up

    result = get_result(job.id)
    assert result == 20, f"Expected 20, got {result}"

if __name__ == "__main__":
    test_worker_executes_job()
    print("✅ test_worker.py passed")
