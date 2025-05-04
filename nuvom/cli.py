# nuvom/cli.py

import typer
from rich import print
from nuvom.config import get_settings
from nuvom.worker import start_worker_pool

app = typer.Typer(help="Nuvom — Task Queue CLI")

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
    start_worker_pool()


def main():
    app()

