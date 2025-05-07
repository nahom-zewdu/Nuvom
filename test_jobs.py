# test_jobs.py

from nuvom import task
from nuvom.worker import start_worker_pool
from nuvom.result_store import get_result, get_error

import threading

@task(retries=9)
def add(a, b):
    return (a + b)

# Start worker threads
threading.Thread(target=start_worker_pool, daemon=True).start()

# Now delay
job_id = add.map([(2, 4),(2, 3),(26, 4),(72, 4),(82, 4),(29, 4),(0, 4),(92, 45),(22, 4)])


# Let the main thread sleep to allow processing
import time
time.sleep(6)

for id in job_id:
    print(get_result(id))
