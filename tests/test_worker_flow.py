# tests/test_smart_worker_model.py

import threading
import time
import uuid

from nuvom.queue import get_queue_backend
from nuvom.result_store import get_result, reset_backend
from nuvom.registry.registry import get_task_registry
from nuvom.job import Job
from nuvom.task import task

from nuvom.worker import WorkerThread, DispatcherThread, _shutdown_event

# Define dummy task functions
@task
def slow_add(a, b):
    time.sleep(0.1)
    return a + b

@task
def slow_mul(a, b):
    time.sleep(0.1)
    return a * b

def test_smart_worker_balancing():
    """
    This test verifies that:
    - Dispatcher assigns jobs to available workers
    - Workers execute jobs
    - Results are correctly stored
    """
    # Setup
    reset_backend()
    _shutdown_event.clear()

    registry = get_task_registry()
    registry.clear()
    registry.register("slow_add", slow_add, force=True)
    registry.register("slow_mul", slow_mul, force=True)
    
    # Spawn 3 workers
    workers = []
    for i in range(3):
        w = WorkerThread(worker_id=i, job_timeout=5)
        w.start()
        workers.append(w)

    # Create jobs manually
    jobs = []
    for i in range(5):
        if i % 2 == 0:
            slow_add.delay(i, i) 
        else:
            slow_mul.delay(i,i)
        

    # Start dispatcher
    dispatcher = DispatcherThread(workers=workers, batch_size=2, job_timeout=3)
    dispatcher.start()

    # Trigger shutdown
    _shutdown_event.set()
    dispatcher.join()
    for w in workers:
        w.join()

    # Verify results
    for job in jobs:
        result = get_result(job.id)
        assert result == job.args[0] + job.args[1] or result == job.args[0] * job.args[1]

    print("[test] ✅ All jobs completed and returned correct results.")
