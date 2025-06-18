# nuvom/cli/commands/list_tasks.py

import typer
from rich.console import Console
from rich.table import Table

from nuvom.discovery.manifest import ManifestManager
from nuvom.registry.registry import get_task_registry, TaskInfo
from nuvom.log import logger

console = Console()
list_app = typer.Typer(name="list", help="List registered @task definitions and their metadata.")

@list_app.command("tasks")
def list_tasks():
    """List @task definitions with their metadata."""
    manifest = ManifestManager()
    discovered_tasks = manifest.load()
    registry = get_task_registry()

    logger.debug("Loaded %d tasks from manifest", len(discovered_tasks))

    table = Table(title="Registered Tasks", show_lines=True)
    table.add_column("Name", style="yellow")
    table.add_column("Module", style="blue")
    table.add_column("Path", style="dim")
    table.add_column("Tags", style="green")
    table.add_column("Description", style="white")

    for task in discovered_tasks:
        task_info: TaskInfo = registry.all().get(task.func_name)
        metadata = task_info.metadata if task_info else {}
        tags = ", ".join(metadata.get("tags", []))
        description = metadata.get("description", "")
        table.add_row(task.func_name, task.module_name, task.file_path, tags, description)

    if not discovered_tasks:
        console.print("[dim]No task definitions found.[/dim]")
        logger.info("No tasks found to list")
    else:
        console.print(table)
        logger.info("Listed %d tasks", len(discovered_tasks))
