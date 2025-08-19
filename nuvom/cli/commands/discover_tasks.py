# nuvom/cli/commands/discover_tasks.py

"""
Scan the project directory for functions decorated with @task or @scheduled_task
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
from nuvom.log import get_logger

console = Console()
logger = get_logger()

discover_app = typer.Typer(
    name="discover",
    help=(
        "Recursively scan for @task and @scheduled_task functions "
        "and refresh .nuvom/manifest.json\n\n"
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
    """Discover @task and @scheduled_task definitions and update the manifest file."""
    root_path = Path(root).resolve()
    console.print(f"[bold]🔍 Scanning tasks in:[/bold] {root_path}")
    logger.debug(
        "Starting task discovery in %s with include=%s and exclude=%s",
        root_path,
        include,
        exclude,
    )

    normal_tasks, scheduled_tasks = discover_tasks(
        root_path=root, include=include, exclude=exclude
    )

    console.print(
        f"[cyan]🔎 Found {len(normal_tasks)} normal task(s) "
        f"and {len(scheduled_tasks)} scheduled task(s).[/cyan]"
    )

    manager = ManifestManager()
    diff = manager.diff_and_save(normal_tasks, scheduled_tasks)

    # Render manifest changes
    def render_changes(category: str, changes: dict) -> None:
        if not (changes["added"] or changes["removed"] or changes["modified"]):
            return

        table = Table(
            title=f"Manifest Changes ({category})", show_lines=True
        )
        table.add_column("Change", style="bold magenta")
        table.add_column("Task Reference", style="yellow")

        for t in changes["added"]:
            table.add_row("[green]+ Added[/green]", str(t))
        for t in changes["removed"]:
            table.add_row("[red]- Removed[/red]", str(t))
        for t in changes["modified"]:
            table.add_row("[blue]~ Modified[/blue]", str(t))

        console.print(table)

    render_changes("tasks", diff["tasks"])
    render_changes("scheduled_tasks", diff["scheduled_tasks"])

    if not diff["saved"]:
        console.print("[dim]No manifest changes detected.[/dim]")
    else:
        logger.info("✅ Manifest updated successfully")
