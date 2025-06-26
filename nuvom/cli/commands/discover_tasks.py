# nuvom/cli/commands/discover_tasks.py
"""
Scan the project directory for functions decorated with @task
and update the manifest file.
"""

import typer
from typing import List
from rich.console import Console
from rich.table import Table
from pathlib import Path

from nuvom.discovery.discover_tasks import discover_tasks
from nuvom.discovery.manifest import ManifestManager
from nuvom.discovery.reference import TaskReference
from nuvom.log import logger

console = Console()

discover_app = typer.Typer(
    name="discover",
    help=(
        "Recursively scan for @task functions and refresh .nuvom/manifest.json\n\n"
        "Examples:\n"
        "  nuvom discover tasks                    # default scan\n"
        "  nuvom discover tasks --include 'app/**' --exclude 'tests/**'\n"
    ),
    rich_help_panel="🌟  Core Commands",
)


@discover_app.command("tasks")
def discover_tasks_cli(
    root: str = ".",
    include: List[str] = typer.Option([], help="Glob patterns to include"),
    exclude: List[str] = typer.Option([], help="Glob patterns to exclude"),
):
    """Discover @task definitions and update the manifest file."""
    root_path = Path(root).resolve()
    console.print(f"[bold]🔍 Scanning tasks in:[/bold] {root_path}")
    logger.debug(
        "Starting task discovery in %s with include=%s and exclude=%s",
        root_path,
        include,
        exclude,
    )

    all_refs: List[TaskReference] = discover_tasks(
        root_path=root, include=include, exclude=exclude
    )
    console.print(f"[cyan]🔎 Found {len(all_refs)} task(s).[/cyan]")

    manager = ManifestManager()
    diff = manager.diff_and_save(all_refs)

    table = Table(title="Manifest Changes", show_lines=True)
    table.add_column("Type", style="bold magenta")
    table.add_column("Task", style="yellow")

    for t in diff["added"]:
        table.add_row("[green]+ Added[/green]", str(t))
    for t in diff["removed"]:
        table.add_row("[red]- Removed[/red]", str(t))
    for t in diff["modified"]:
        table.add_row("[blue]~ Modified[/blue]", str(t))

    if not (diff["added"] or diff["removed"] or diff["modified"]):
        console.print("[dim]No manifest changes detected.[/dim]")
    else:
        console.print(table)
        logger.info(
            "✅ Manifest updated with %d additions, %d removals, %d modifications",
            len(diff["added"]),
            len(diff["removed"]),
            len(diff["modified"]),
        )
