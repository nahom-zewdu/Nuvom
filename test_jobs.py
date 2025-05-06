# test_jobs.py

from nuvom import task
from nuvom.worker import start_worker_pool
import threading

@task
def greet(name):
    print(f"Hello, {name}")

# Start worker threads
threading.Thread(target=start_worker_pool, daemon=True).start()

# Now delay
greet.delay("Shady")

# Let the main thread sleep to allow processing
import time
time.sleep(5)
