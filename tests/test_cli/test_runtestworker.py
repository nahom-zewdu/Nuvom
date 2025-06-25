# tests/cli/test_runtestworker.py

import json
import tempfile
from pathlib import Path

from typer.testing import CliRunner
from nuvom.cli.cli import app
from nuvom.task import task

runner = CliRunner()

# Register a simple test task
@task()
def add(x, y):
    return x + y

@task()
def fail_task():
    raise RuntimeError("Intentional failure")


def write_job_file(data: dict) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
    json.dump(data, tmp)
    tmp.close()
    return Path(tmp.name)


def test_runtestworker_success():
    job_file = write_job_file({
        "func_name": "add",
        "args": [2, 3]
    })

    result = runner.invoke(app, ["runtestworker", "run", str(job_file)])
    assert result.exit_code == 0
    assert "Result:" in result.stdout
    assert "5" in result.stdout


def test_runtestworker_failure():
    job_file = write_job_file({
        "func_name": "fail_task"
    })

    result = runner.invoke(app, ["runtestworker", "run", str(job_file)])
    assert result.exit_code != 0
    assert "FAILED" in result.stdout
    assert "RuntimeError" in result.stdout


def test_runtestworker_missing_func_name():
    job_file = write_job_file({
        "args": [1, 2]
    })

    result = runner.invoke(app, ["runtestworker", "run", str(job_file)])
    assert result.exit_code != 0
    assert "Missing 'func_name'" in result.stdout
