# nuvom/cli/commands/plugin.py
"""
`nuvom plugin …` – manage and inspect the plugin system.
Currently only implements **status**; scaffold/test will be added next.
"""

from __future__ import annotations

from pathlib import Path
import typer
from rich.table import Table
from rich.console import Console
from datetime import datetime
import importlib.util
import traceback

from nuvom.plugins.loader import load_plugins
from nuvom.plugins.registry import REGISTRY, ensure_builtins_registered
from nuvom.plugins.contracts import Plugin, API_VERSION

plugin_app = typer.Typer(
    name="plugin",
    help=(
        "Manage Nuvom plugins (status, scaffold, test).\n\n"
        "Examples:\n"
        "  nuvom plugin status                      # Show all loaded plugins\n"
        "  nuvom plugin scaffold my_redis_backend   # Create plugin stub\n"
        "  nuvom plugin test nuvom_hello.plugin     # Test installed plugin\n"
        "  nuvom plugin test ./my_plugin.py         # Test from file\n"
    ),
    rich_help_panel="🔌 Plugin System",
)
console = Console()


@plugin_app.command("status")
def status() -> None:
    """
    Display all plugins that are registered / loaded in the current process.
    """
    
    ensure_builtins_registered()
    load_plugins()                           # ensure everything is imported

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Capability")
    table.add_column("Name")
    table.add_column("Provider")
    table.add_column("Loaded At")

    now = datetime.now().strftime("%H:%M:%S")

    for cap, bucket in REGISTRY._caps.items():               # type: ignore[attr-defined]
        for name, obj in bucket.items():
            provider = getattr(obj, "__class__", type(obj)).__name__
            table.add_row(cap, name, provider, now)

    if REGISTRY._caps:                                   # type: ignore[attr-defined]
        console.print(table)
    else:
        console.print(table)
        console.print("[yellow]No plugins loaded.[/yellow]")


@plugin_app.command("scaffold")
def scaffold(
    name: str = typer.Argument(..., help="Short name for your plugin (e.g. my_sqs_backend)"),
    out: Path = typer.Option(".", help="Directory to write the plugin file"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file exists"),
    capability: str = typer.Option("queue_backend", "--capability", "-c", help="Capability this plugin provides"),
    test: bool = typer.Option(False, "--test", "-t", help="Run `plugin test` after scaffolding"),
):
    """
    Scaffold a new plugin stub that implements the Plugin protocol.
    """
    if not name.isidentifier():
        console.print(f"[red]❌ Invalid plugin name: {name}[/red]")
        raise typer.Exit(code=1)

    class_name = "".join(part.capitalize() for part in name.split("_"))
    filename = out / f"{name}.py"

    if filename.exists() and not force:
        console.print(f"[yellow]⚠ File {filename} already exists. Use --force to overwrite.[/yellow]")
        raise typer.Exit(code=1)

    plugin_stub = f'''\

from nuvom.plugins.contracts import Plugin

class {class_name}(Plugin):
    api_version = "1.0"
    name = "{name}"
    provides = ["{capability}"]      # "queue_backend", "result_backend", or other
    requires = []                    # List dependencies this plugin needs

    def start(self, settings: dict) -> None:
        # Initialize plugin (e.g. connect to service, configure hooks)
        pass

    def stop(self) -> None:
        # Cleanup plugin resources
        pass
'''

    try:
        out.mkdir(parents=True, exist_ok=True)
        filename.write_text(plugin_stub.strip() + "\n", encoding="utf-8")
        console.print(f"[green]✅ Plugin scaffold created:[/green] {filename}")
    except Exception as e:
        console.print(f"[red]❌ Failed to write file:[/red] {e}")
        raise typer.Exit(code=1)

    if test:
        from nuvom.cli.cli import app as main_app
        from typer.testing import CliRunner
        console.print("[blue]Running plugin test...[/blue]")
        result = CliRunner().invoke(main_app, ["plugin", "test", str(filename)])
        console.print(result.output, highlight=False)
        if result.exit_code != 0:
            raise typer.Exit(code=1)




@plugin_app.command("test")
def test_plugin(
    target: str = typer.Argument(..., help="Path to plugin .py file OR python.module path"),
) -> None:
    """
    Validate a plugin and run its `start/stop` hooks.

    • Works with a standalone `.py` file or an installed module path.
    • Emits a non‑zero exit‑code on failure (good for CI).
    """
    from nuvom.plugins.contracts import Plugin

    # ------------------------
    # Step 1: Load the module
    # ------------------------
    file_path = Path(target)
    try:
        if file_path.exists():  # Local .py file
            spec = importlib.util.spec_from_file_location("plugin_under_test", str(file_path))
            if spec is None or spec.loader is None:
                raise RuntimeError("Could not load plugin file.")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
        else:  # Python module path
            module = importlib.import_module(target)
    except Exception as exc:
        console.print(f"[red]❌ Import failed:[/red] {exc}")
        raise typer.Exit(code=1)

    # ------------------------
    # Step 2: Find Plugin subclass
    # ------------------------
    plugin = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
            plugin = attr()
            break

    if not plugin:
        console.print("[red]❌ No valid Plugin subclass found.[/red]")
        raise typer.Exit(code=1)

    # ------------------------
    # Step 3: Validate metadata
    # ------------------------
    errors = []
    if plugin.api_version.split(".")[0] != API_VERSION.split(".")[0]:
        errors.append(f"API version mismatch: plugin={plugin.api_version}, core={API_VERSION}")
    if not plugin.provides:
        errors.append("Missing `provides`.")
    if not callable(getattr(plugin, "start", None)):
        errors.append("Missing or invalid `start()`.")
    if not callable(getattr(plugin, "stop", None)):
        errors.append("Missing or invalid `stop()`.")

    if errors:
        for err in errors:
            console.print(f"[red]❌ {err}[/red]")
        raise typer.Exit(code=1)

    # ------------------------
    # Step 4: Run start/stop hooks
    # ------------------------
    try:
        plugin.start({})
        plugin.stop()
    except Exception as e:
        console.print(f"[red]❌ start() or stop() raised exception:[/red] {e}")
        traceback.print_exc()
        raise typer.Exit(code=1)

    # ✅ SUCCESS
    console.print(f"[green]✅ Plugin {plugin.name} validated successfully.[/green]")
