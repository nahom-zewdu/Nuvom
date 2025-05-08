# nuvom/cli.py

import typer
from rich import print
import threading
import time

from nuvom import __version__
from nuvom.config import get_settings
from nuvom.worker import start_worker_pool
from nuvom.result_store import get_result, get_error

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
def runworker():
    """
    Start a local worker pool to process jobs.
    """
    
    print("[yellow]Starting worker...[/yellow]")
    
    # Start worker threads
    start_worker_pool()

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

def main():
    app()

