# tests/test_retry_delay.py
import time
import pytest

from nuvom.task import task
from nuvom.job import Job
from nuvom.queue import enqueue, clear
from nuvom.worker import WorkerThread, DispatcherThread
from nuvom.result_store import get_result
from nuvom.config import override_settings
from nuvom.registry.registry import get_task_registry

# --- global attempt counter ------------------------------------------------
attempt_counter = {"count": 0}

@task
def flaky_task():
    attempt_counter["count"] += 1
    if attempt_counter["count"] < 2:
        raise ValueError("fail once")
    return "recovered"


# --- auto-reset fixture -----------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_env():
    """
    • Reset attempt counter & in-memory queue
    • Force MEMORY queue/result back-ends for speed & isolation
    """
    attempt_counter["count"] = 0
    clear()
    override_settings(
        retry_delay_secs=2,
        max_workers=1,
    )
    yield
    clear()


# helper: make sure the task is in the registry for THIS process
def _ensure_registered():
    reg = get_task_registry()
    reg.register("flaky_task", flaky_task, force=True)


# --- Tests -----------------------------------------------------------------
def test_job_is_retried_after_delay():
    _ensure_registered()

    job = Job(func_name="flaky_task", retries=1, retry_delay_secs=2)
    enqueue(job)

    worker = WorkerThread(worker_id=0, job_timeout=1)
    dispatcher = DispatcherThread([worker], batch_size=1, job_timeout=1)
    worker.start(); dispatcher.start()

    time.sleep(0.5);  assert attempt_counter["count"] == 1  # first attempt
    time.sleep(1);  assert attempt_counter["count"] == 1  # not yet retried
    time.sleep(1);  assert attempt_counter["count"] == 2  # retried & ok

    assert get_result(job.id) == "recovered"

    worker.join(1); dispatcher.join(1)


def test_job_skips_retry_if_delay_not_ready():
    _ensure_registered()

    job = Job(func_name="flaky_task", retries=1, retry_delay_secs=3)
    enqueue(job)

    worker = WorkerThread(worker_id=0, job_timeout=1)
    dispatcher = DispatcherThread([worker], batch_size=1, job_timeout=1)
    worker.start(); dispatcher.start()

    time.sleep(2)
    assert attempt_counter["count"] == 1          # only first attempt
    assert get_result(job.id) is None             # no retry yet

    worker.join(1); dispatcher.join(1)
