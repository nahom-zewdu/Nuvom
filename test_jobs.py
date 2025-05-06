# test_jobs.py

from nuvom import task
from nuvom.worker import start_worker_pool
from nuvom.result_store import get_result, get_error

import threading

@task
def add(a, b):
    print("Hello, You")
    return (a + b)

# Start worker threads
threading.Thread(target=start_worker_pool, daemon=True).start()

# Now delay
job_id = add.delay(2, 4)


# Let the main thread sleep to allow processing
import time
time.sleep(5)

print(get_result(job_id))
