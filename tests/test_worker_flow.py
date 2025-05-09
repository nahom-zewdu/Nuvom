import time
import threading
from nuvom.task import task
from nuvom.queue import get_global_queue
from nuvom.worker import worker_loop, _shutdown_event
from nuvom.result_store import get_result, get_error, reset_backend
from nuvom.config import get_settings

# Set config to use memory backend explicitly
get_settings().result_backend = "memory"
reset_backend() # Force re-init backend

@task
def add(x, y):
    return x + y

def test_worker_executes_task_and_stores_result():
    # Clear shutdown flag in case it was set
    _shutdown_event.clear()

    # Enqueue task
    job = add.delay(2, 3)

    # Start worker in a thread
    t = threading.Thread(target=worker_loop, args=(0, 1, 1), daemon=True)
    t.start()

    # Wait up to 5 seconds for result
    for _ in range(10):
        result = get_result(job.id)
        if result is not None:
            break
        time.sleep(0.5)
    else:
        assert False, "Worker did not complete job in time"

    assert result == 5
    assert get_error(job.id) is None

    # Shutdown worker
    _shutdown_event.set()
    t.join(timeout=2)
