# tests/test_cli/test_plugin_status.py

from typer.testing import CliRunner
import pytest

from nuvom.cli.cli import app

runner = CliRunner()

@pytest.fixture(autouse=True)
def reset_plugins():
    """
    Test isolation: clear plugin registry and loader cache before each test.
    """
    from nuvom.plugins.registry import REGISTRY
    from nuvom.plugins.loader import _LOADED

    REGISTRY._caps.clear()       # wipe registry state
    _LOADED.clear()              # force re‑load on next call

    yield                        # ← test runs here

    REGISTRY._caps.clear()
    _LOADED.clear()


def test_plugin_status_prints_table():
    """
    Ensure `nuvom plugin status` prints a table and exits cleanly.
    """
    result = runner.invoke(app, ["plugin", "status"])
    assert result.exit_code == 0
    assert "Capability" in result.output
    assert "Name" in result.output
    assert "Provider" in result.output
    assert "Loaded At" in result.output


def test_plugin_status_no_plugins(monkeypatch):
    """
    Simulate no plugins registered — should print 'No plugins loaded.'
    """
    monkeypatch.setattr("nuvom.plugins.registry.REGISTRY._caps", {})
    result = runner.invoke(app, ["plugin", "status"])
    assert result.exit_code == 0
    assert "No plugins loaded" in result.output
