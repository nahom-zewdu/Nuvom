# nuvom/cli.py

import typer
from rich import print
import threading
import time
from pathlib import Path

from nuvom import __version__
from nuvom.config import get_settings
from nuvom.worker import start_worker_pool
from nuvom.result_store import get_result, get_error
from nuvom.cli.commands import discover_tasks, list_tasks

app = typer.Typer(help="Nuvom — Task Queue CLI")

@app.command()
def version():
    """Show current Nuvom version."""
    print(f"[bold green]NUVOM v{__version__}[/bold green]")

@app.command()
def config():
    """
    Show current Nuvom config loaded from env/.env.
    """
    settings = get_settings()
    print("[bold green]Nuvom Configuration:[/bold green]")
    for key, val in settings.summary().items():
        print(f"[cyan]{key}[/cyan] = {val}")

@app.command()
def runworker(dev: bool = typer.Option(False, help="Enable dev mode with manifest auto-reload")):
    """
    Start a local worker pool to process jobs.
    If --dev is used, hot reloads tasks on manifest file changes.
    """
    print("[yellow]🚀 Starting worker...[/yellow]")

    observer = None
    if dev:
        from nuvom.watcher import ManifestChangeHandler
        from watchdog.observers import Observer

        manifest_path = Path(".nuvom/manifest.json").resolve()
        handler = ManifestChangeHandler(manifest_path)
        observer = Observer()
        observer.schedule(handler, manifest_path.parent, recursive=False)
        observer.start()
        print("[blue]🌀 Dev mode active — watching manifest for changes...[/blue]")

    try:
        start_worker_pool()
    finally:
        if observer:
            observer.stop()
            observer.join()


@app.command()
def status(job_id: str):
    """
    Check the status of a job by its ID.
    """
    error = get_error(job_id)
    if error:
        print(f"[bold red]❌ FAILED:[/bold red] {error}")
        return

    result = get_result(job_id)
    if result is not None:
        print(f"[bold green]✅ SUCCESS:[/bold green] {result}")
        return

    print("[cyan]🕒 PENDING[/cyan]")

app.add_typer(discover_tasks.discover_app, name="discover")
app.add_typer(list_tasks.list_app, name="list")

def main():
    app()

