# nuvom/cli.py

import typer
from rich import print
from nuvom.config import get_settings

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
    (Stubbed for now.)
    """
    print("[yellow]Starting worker...[/yellow]")
    settings = get_settings()
    print(f"→ Max workers: {settings.max_workers}")
    print(f"→ Batch size: {settings.batch_size}")
    print(f"→ Timeout: {settings.job_timeout_secs}s")
    # TODO: Call actual worker runner here later.


def main():
    app()

