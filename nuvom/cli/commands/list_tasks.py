# nuvom/cli/commands/list_tasks.py

import typer
from typing import List
from rich import print
from rich.table import Table
from pathlib import Path

from nuvom.discovery.manifest import ManifestManager

list_app = typer.Typer(name="list", help="Scan project for @tasks and return list of tasks.")

@list_app.command("tasks")
def list_tasks(
):
    """
    Discover @task definitions and Print list of tasks.
    """
    
    manifest = ManifestManager()
    discovered_tasks = manifest.load()

    # Display changes
    table = Table(title="List of tasks", show_lines=True)
    table.add_column("Name", style="yellow")
    table.add_column("Module", style="blue")
    table.add_column("Path", style="blue")

    for task in discovered_tasks:
        table.add_row(f"{task.func_name}", task.module_name, task.file_path)
    
    
    if not discovered_tasks:
        print("[dim]No task definition found.[/dim]")
    else:
        print(table)