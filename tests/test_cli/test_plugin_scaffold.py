# tests/test_cli/test_plugin_scaffold.py

import shutil
from pathlib import Path
from nuvom.cli.cli import app
from typer.testing import CliRunner

runner = CliRunner()

def test_plugin_scaffold_creates_file(tmp_path):
    plugin_name = "custom_plugin"
    result = runner.invoke(app, ["plugin", "scaffold", plugin_name, "--out", str(tmp_path)])
    
    file_path = tmp_path / f"{plugin_name}.py"
    assert result.exit_code == 0
    assert file_path.exists()
    assert "class CustomPlugin(Plugin):" in file_path.read_text()
