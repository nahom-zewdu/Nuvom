# tests/test_timeout_policy.py

import time
import pytest

from nuvom.job import Job
from nuvom.task import task
from nuvom.queue import enqueue, clear
from nuvom.result_store import get_result, get_error
from nuvom.worker import WorkerThread, DispatcherThread
from nuvom.config import override_settings
from nuvom.registry.registry import get_task_registry

# --- Timeout Task -----------------------------------------------------
@task
def sleepy():
    time.sleep(2)
    return "done"

def _ensure_registered():
    get_task_registry().register("sleepy", sleepy, force=True)

# --- Test Setup -------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset():
    _ensure_registered()
    clear()
    override_settings(
        job_timeout_secs=1,
        retry_delay_secs=1,
        result_backend="memory",
        queue_backend="memory",
        max_workers=1,
    )
    yield
    clear()

def _run_job(job):
    enqueue(job)
    worker = WorkerThread(worker_id=0, job_timeout=1)
    dispatcher = DispatcherThread([worker], batch_size=1, job_timeout=1)
    worker.start(); dispatcher.start()
    time.sleep(3)
    worker.join(1); dispatcher.join(1)

# --- Tests ------------------------------------------------------------

def test_timeout_policy_fail():
    job = Job(func_name="sleepy", retries=0, timeout_policy="fail")
    _run_job(job)
    assert get_result(job.id) is None
    assert "timed out" in get_error(job.id).get('message')

def test_timeout_policy_ignore():
    job = Job(func_name="sleepy", retries=0, timeout_policy="ignore")
    _run_job(job)
    assert get_result(job.id) is None  # success but returns None
    assert get_error(job.id) is None

def test_timeout_policy_retry():
    job = Job(func_name="sleepy", retries=1, retry_delay_secs=1, timeout_policy="retry")
    _run_job(job)
    assert get_result(job.id) is None  # retries eventually fail (task always sleeps too long)
    assert "timed out" in get_error(job.id).get('message')
