# test_jobs.py

from nuvom import task
from nuvom.worker import start_worker_pool
from nuvom.result_store import get_result, get_error

import threading

@task(retries=9)
def add(a, b):
    return (a + b) / 0

# Start worker threads
threading.Thread(target=start_worker_pool, daemon=True).start()

# Now delay
job_id = add.delay(2, 4)


# Let the main thread sleep to allow processing
import time
time.sleep(5)

print(job_id, get_result(job_id))
