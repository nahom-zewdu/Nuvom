import typer
from typing import List
from rich import print
from rich.table import Table
from pathlib import Path

from nuvom.discovery.discover_tasks import discover_tasks
from nuvom.discovery.reference import TaskReference
from nuvom.discovery.manifest import ManifestManager

discover_app = typer.Typer(name="discover", help="Scan project for @task definitions")

@discover_app.command("tasks")
def discover_tasks_cli(
    root: str = ".",
    include: List[str] = typer.Option([], help="Glob patterns to include"),
    exclude: List[str] = typer.Option([], help="Glob patterns to exclude")
):
    """
    Discover @task definitions and update the manifest.
    """
    root_path = Path(root).resolve()
    print(f"[bold]🔍 Scanning tasks in:[/bold] {root_path}")

    all_refs: List[TaskReference] = discover_tasks(root_path=root, include=include, exclude=exclude)

    print(f"[cyan]🔎 Found {len(all_refs)} task(s).[/cyan]")

    manager = ManifestManager()
    diff = manager.diff_and_save(all_refs)

    # Display changes
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
        print("[dim]No manifest changes detected.[/dim]")
    else:
        print(table)
        print("[green]✅ Manifest updated.[/green]")
