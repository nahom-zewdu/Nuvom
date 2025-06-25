import pytest
from typer.testing import CliRunner
from nuvom.cli.cli import app
from nuvom.result_store import set_result, reset_backend

runner = CliRunner()

@pytest.fixture(autouse=True)
def clear_backend():
    reset_backend()
    yield
    reset_backend()

def test_inspect_command_runs_and_outputs_table():
    set_result("job-inspect-test", 'test', 100, args=[1], kwargs={"a": 2}, created_at="2024-01-01", attempts=1)
    result = runner.invoke(app, ["inspect", "job", "job-inspect-test"])
    assert result.exit_code == 0
    assert "job-inspect-test" in result.stdout
    assert "100" in result.stdout
