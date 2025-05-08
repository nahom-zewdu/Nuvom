# test_jobs.py

from nuvom import task
from nuvom.worker import start_worker_pool
from nuvom.result_store import get_result, get_error

import threading

@task(retries=2, store_result=True)
def add(a, b):
    return (a + b)

# Start worker threads
threading.Thread(target=start_worker_pool, daemon=True).start()

# Now delay
jobs = add.map([(2, 4),(2, 3),(26, 4),(72, 4),(82, 4),(29, 4),(0, 4),(92, 45),(22, 4)])

print("Waiting for result...")
try:
    for job in jobs:
        print(job.get())
except TimeoutError:
    print("Job timed out")
except RuntimeError as e:
    print("Job failed:", e)
    