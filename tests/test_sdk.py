# tests/test_sdk.py

import time
import pytest

from nuvom.task import task
from nuvom.job import Job
from nuvom.sdk import get_job_status, retry_job
from nuvom.result_store import get_error
from nuvom.queue import enqueue, clear
from nuvom.worker import WorkerThread, DispatcherThread
from nuvom.registry.registry import get_task_registry

task_attempts = {"count": 0}

@task
def flaky():
    task_attempts["count"] += 1
    raise ValueError("broken")

def _ensure_registered():
    get_task_registry().register("flaky", flaky, force=True)

@pytest.fixture(autouse=True)
def reset_env():
    task_attempts["count"] = 0
    clear()
    yield
    clear()

def test_get_job_status_success():
    _ensure_registered()

    job = Job("flaky", retries=0)
    enqueue(job)

    w = WorkerThread(0, job_timeout=1)
    d = DispatcherThread([w], batch_size=1, job_timeout=1)
    w.start(); d.start()
    time.sleep(1.5)

    meta = get_job_status(job.id)
    assert meta["func_name"] == "flaky"
    assert meta["status"] == "FAILED"
    assert "error" in meta

    w.join(1); d.join(1)

def test_retry_job_success():
    _ensure_registered()

    job = Job("flaky", retries=1)
    enqueue(job)

    w = WorkerThread(0, job_timeout=1)
    d = DispatcherThread([w], batch_size=1, job_timeout=1)
    w.start(); d.start()
    time.sleep(1.5)

    new_id = retry_job(job.id)
    assert isinstance(new_id, str)
    assert new_id != job.id

    w.join(1); d.join(1)

def test_retry_job_no_more_retries():
    _ensure_registered()
    job = Job("flaky", retries=0)
    enqueue(job)

    w = WorkerThread(0, job_timeout=1)
    d = DispatcherThread([w], batch_size=1, job_timeout=1)
    w.start(); d.start()
    time.sleep(1.5)

    assert retry_job(job.id) is None
    w.join(1); d.join(1)

def test_get_job_status_invalid_id():
    with pytest.raises(KeyError):
        get_job_status("not-a-job")

def test_retry_job_invalid_id():
    with pytest.raises(KeyError):
        retry_job("not-a-job")
