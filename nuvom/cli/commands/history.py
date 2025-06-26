import typer
from rich.table import Table
from rich.console import Console
from typing import Optional

from nuvom.result_store import get_backend

history_app = typer.Typer(
    name="history",
    help=(
        "Show recent jobs (reads backend metadata).\n\n"
        "Examples:\n"
        "  nuvom history recent --limit 20\n"
        "  nuvom history recent --status FAILED\n"
    ),
)

console = Console()


@history_app.command("recent")
def show_recent(
    limit: int = typer.Option(20),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status: SUCCESS | FAILED | PENDING",
        case_sensitive=False,
        ),
    ):
    """Pretty table of recent jobs (newest first)."""
    
    backend = get_backend()

    if not hasattr(backend, "list_jobs"):
        console.print("[red]⚠️ This backend does not support job history.[/red]")
        raise typer.Exit(1)

    jobs = backend.list_jobs()

    if status:
        status = status.upper()
        jobs = [j for j in jobs if j.get("status") == status]

    jobs = sorted(jobs, key=lambda j: j.get("created_at", 0), reverse=True)

    if limit:
        jobs = jobs[:limit]

    table = Table(title="Nuvom Job History")
    table.add_column("Job ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Task", style="green")
    table.add_column("result", style="green")
    table.add_column("error", style="red")
    table.add_column("args", style="yellow")
    table.add_column("Created", style="dim")
    table.add_column("Completed", style="dim")

    for job in jobs:
        table.add_row(
            job.get("job_id", "N/A"),
            job.get("status", "N/A"),
            job.get("func_name", "N/A"),
            str(job.get("result", "N/A")), #int is Not Renderable; a string or other renderable object is required
            job.get("error", "N/A"),
            str(job.get("args", "N/A")), #list is Not Renderable; a string or other renderable object is required
            f"{job.get('created_at', 0)}",
            f"{job.get('completed_at', 0)}",
        )

    if not jobs:
        console.print("[yellow]No job history found.[/yellow]")
    else:
        console.print(table)
