# tests/test_cli/test_plugin_test.py

from pathlib import Path
import textwrap
from typer.testing import CliRunner
from nuvom.cli.cli import app

runner = CliRunner()


def test_plugin_test_passes(tmp_path: Path):
    """
    Create a minimal Plugin implementation on disk and run:

        nuvom plugin test <file>

    Expect: exit‑code 0 and success message in output.
    """
    plugin_file = tmp_path / "test_plugin.py"
    plugin_file.write_text(
        textwrap.dedent(
            """
            from nuvom.plugins.contracts import Plugin

            class TestPlugin(Plugin):
                api_version = "1.0"
                name = "test_plugin"
                provides = ["queue_backend"]
                requires = []

                def start(self, settings): ...
                def stop(self): ...
            """
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["plugin", "test", str(plugin_file)])

    assert result.exit_code == 0
    assert "✅ Plugin test_plugin validated successfully." in result.output
