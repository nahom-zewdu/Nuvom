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
    import textwrap

    # Step 1: Create a temp task module with fail_task
    temp_task_module = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
    temp_task_module.write(textwrap.dedent("""
        from nuvom.task import task

        @task()
        def fail_task():
            raise RuntimeError("Intentional failure")
    """))
    temp_task_module.close()

    # Step 2: Create the job file
    job_file = write_job_file({
        "func_name": "fail_task"
    })

    # Step 3: Pass --task-module to the CLI
    result = runner.invoke(app, [
        "runtestworker", "run", str(job_file),
        "--task-module", temp_task_module.name
    ])

    # Step 4: Validate output
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
