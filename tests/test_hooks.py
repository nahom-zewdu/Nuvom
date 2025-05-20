# tests/test_hooks.py

import time
from nuvom import task
from nuvom.worker import start_worker_pool

from multiprocessing import Process

def start_workers_in_process():
    p = Process(target=start_worker_pool, daemon=True)
    p.start()


start_workers_in_process()
time.sleep(2)


CALL_LOG = []

@task()
def reset_log_task():
    CALL_LOG.clear()

@task()
def log_task(msg):
    CALL_LOG.append(msg)

@task()
def successful_task(x):
    return x * 2

@task()
def failing_task():
    raise ValueError("fail")

@task()
def long_task():
    time.sleep(5)

@task(
    before_job=lambda job: CALL_LOG.append("before"),  # type: ignore
    after_job=lambda job, res: CALL_LOG.append("after"),  # type: ignore
    on_error=lambda job, err: CALL_LOG.append("error")  # type: ignore
)
def task_with_hooks(x):
    return x + 1

def test_success_hooks():
    reset_log_task.delay().get(timeout=2)
    task_with_hooks.delay(5).get(timeout=2)
    assert CALL_LOG == ["before", "after"]

def test_failure_hooks():
    reset_log_task.delay().get(timeout=2)
    try:
        failing_task.delay().get(timeout=2)
    except RuntimeError:
        pass
    assert "error" in CALL_LOG

def test_timeout_hooks():
    reset_log_task.delay().get(timeout=2)
    try:
        long_task.delay(timeout_secs=1).get(timeout=2)
    except TimeoutError:
        pass
    assert "error" in CALL_LOG
