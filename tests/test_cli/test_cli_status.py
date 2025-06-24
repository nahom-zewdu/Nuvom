# tests/test_cli/test_cli_status.py

import pytest
from typer.testing import CliRunner
from nuvom.cli.cli import app
from nuvom.result_store import set_result, set_error

runner = CliRunner()

def test_status_success():
    job_id = "job-success"
    result = {"data": 123}
    set_result(job_id, result)
    
    result = runner.invoke(app, ["status", job_id])
    assert result.exit_code == 0
    assert "SUCCESS:" in result.stdout

def test_status_failure():
    job_id = "job-fail"
    set_error(job_id, "Something broke")
    
    result = runner.invoke(app, ["status", job_id])
    assert result.exit_code == 0
    assert "FAILED:" in result.stdout

def test_status_pending():
    job_id = "job-pending"
    result = runner.invoke(app, ["status", job_id])
    
    assert result.exit_code == 0
    assert "PENDING" in result.stdout
