# nuvom/cli/commands/plugins_status.py

import typer
from rich.table import Table
from rich.console import Console

from nuvom.plugins.loader import load_plugins, _LOADED
from nuvom.plugins.registry import REGISTRY

console = Console()
plugins_app = typer.Typer(name="plugins", help="Plugin utilities")

@plugins_app.command("status")
def status():
    """Show which plugins are active and what they provide."""
    load_plugins()      # ensure everything is imported

    tbl = Table(title="Nuvom Plugins")
    tbl.add_column("Name", style="cyan")
    tbl.add_column("Provides", style="green")
    tbl.add_column("Loaded", style="bold")

    for cap, bucket in REGISTRY._caps.items():
        for name, obj in bucket.items():
            loaded = "✅" if name in _LOADED else "⚠️ (legacy)"
            tbl.add_row(name, cap, loaded)

    console.print(tbl)
