# nuvom/cli/cli.py

import typer
import threading
import time
from pathlib import Path
from rich.console import Console

from nuvom import __version__
from nuvom.config import get_settings
from nuvom.worker import start_worker_pool
from nuvom.result_store import get_result, get_error
from nuvom.cli.commands import discover_tasks, list_tasks, inspect_job
from nuvom.log import logger

console = Console()
app = typer.Typer(help="Nuvom — Task Queue CLI")

@app.command()
def version():
    """Show current Nuvom version."""
    console.print(f"[bold green]NUVOM v{__version__}[/bold green]")

@app.command()
def config():
    """Show current Nuvom config loaded from env/.env."""
    settings = get_settings()
    console.print("[bold green]Nuvom Configuration:[/bold green]")
    for key, val in settings.summary().items():
        console.print(f"[cyan]{key}[/cyan] = {val}")

@app.command()
def runworker(dev: bool = typer.Option(False, help="Enable dev mode with manifest auto-reload")):
    """Start a local worker pool to process jobs."""
    console.print("[yellow]🚀 Starting worker...[/yellow]")
    logger.info("Starting worker pool with dev=%s", dev)

    observer = None
    if dev:
        from nuvom.watcher import ManifestChangeHandler
        from watchdog.observers import Observer

        manifest_path = Path(".nuvom/manifest.json").resolve()
        handler = ManifestChangeHandler(manifest_path)
        observer = Observer()
        observer.schedule(handler, manifest_path.parent, recursive=False)
        observer.start()
        console.print("[blue]🌀 Dev mode active — watching manifest for changes...[/blue]")
        logger.debug("Manifest watcher started on %s", manifest_path)

    try:
        start_worker_pool()
    finally:
        if observer:
            observer.stop()
            observer.join()
            logger.debug("Manifest watcher stopped")

@app.command()
def status(job_id: str):
    """Check the status of a job by its ID."""
    error = get_error(job_id)
    if error:
        console.print(f"[bold red]❌ FAILED:[/bold red] {error}")
        logger.warning("Job %s failed: %s", job_id, error)
        return

    result = get_result(job_id)
    if result is not None:
        console.print(f"[bold green]✅ SUCCESS:[/bold green] {result}")
        logger.info("Job %s succeeded: %s", job_id, result)
        return

    console.print("[cyan]🕒 PENDING[/cyan]")
    logger.info("Job %s is pending", job_id)

app.add_typer(discover_tasks.discover_app, name="discover")
app.add_typer(list_tasks.list_app, name="list")
app.add_typer(inspect_job.inspect_app, name="inspect")

def main():
    app()
