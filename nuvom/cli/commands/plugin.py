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

from nuvom.plugins.loader import load_plugins
from nuvom.plugins.registry import REGISTRY, ensure_builtins_registered

plugin_app = typer.Typer(help="Manage Nuvom plugins (load status, scaffold, test).")
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
):
    """
    Scaffold a new plugin stub that implements the Plugin protocol.
    """
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
    provides = ["queue_backend"]      # or "result_backend"
    requires = []                     # add any dependencies if needed

    def start(self, settings: dict) -> None:
        pass

    def stop(self) -> None:
        pass
'''

    try:
        out.mkdir(parents=True, exist_ok=True)
        filename.write_text(plugin_stub.strip() + "\n", encoding="utf-8")
        console.print(f"[green]✅ Plugin scaffold created:[/green] {filename}")
    except Exception as e:
        console.print(f"[red]❌ Failed to write file:[/red] {e}")
        raise typer.Exit(code=1)
