# nuvom/cli/commands/plugin.py
"""
`nuvom plugin …` – manage and inspect the plugin system.
Currently only implements **status**; scaffold/test will be added next.
"""

from __future__ import annotations

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
