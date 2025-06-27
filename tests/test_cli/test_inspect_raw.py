# tests/cli/test_inspect_raw.py

import time
from typer.testing import CliRunner

from nuvom.task import task
from nuvom.job import Job
from nuvom.queue import enqueue, clear
from nuvom.worker import WorkerThread, DispatcherThread
from nuvom.cli.cli import app
from nuvom.registry.registry import get_task_registry

runner = CliRunner()

@task
def boom():
    raise RuntimeError("kaboom")

def _run_fail_job():
    get_task_registry().register("boom", boom, force=True)
    job = Job("boom", retries=0)
    enqueue(job)
    w = WorkerThread(0, job_timeout=1)
    d = DispatcherThread([w], batch_size=1, job_timeout=1)
    w.start(); d.start()
    time.sleep(1.5)
    w.join(1); d.join(1)
    return job.id

def test_inspect_raw_with_traceback():
    clear()
    job_id = _run_fail_job()
    result = runner.invoke(app, ["inspect", "job", job_id, "--format", "raw"])
    assert result.exit_code == 0
    assert "Traceback (raw)" in result.stdout
    assert "RuntimeError" in result.stdout
