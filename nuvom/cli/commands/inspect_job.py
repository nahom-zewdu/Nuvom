# nuvom/cli/commands/inspect_job.py
"""
Inspect a completed job by ID and display full metadata.

Supported output formats:
    • table  (default)
    • json
    • raw   ← NEW: pretty JSON + traceback panel
"""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from nuvom.result_store import get_backend
from nuvom.serialize import deserialize
from nuvom.log import logger

inspect_app = typer.Typer(
    name="inspect",
    help="Inspect a completed job’s metadata (result, error, tracebacks, etc.).",
)

console = Console()


@inspect_app.command("job")
def inspect_job(
    job_id: str,
    format: Optional[str] = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table (default), json, raw",  # NEW: mention raw
    ),
):
    """
    Inspect the stored metadata for a finished job.
    """
    backend = get_backend()
    metadata = getattr(backend, "get_full", lambda _id: None)(job_id)

    if not metadata:
        console.print(f"[bold red]❌ No metadata found for job:[/bold red] {job_id}")
        raise typer.Exit(code=1)

    if format == "json":
        console.print_json(data=metadata)

    elif format == "raw":  # NEW
        _render_raw(metadata)

    elif format == "table":
        _render_table(metadata)

    else:
        console.print(f"[red]Invalid format:[/red] {format}")
        raise typer.Exit(code=1)

    logger.debug("Inspected job %s with format='%s'", job_id, format)


# ---------------------------------------------------------------------------
 

def _render_table(data: dict):
    """
    Render job metadata in a Rich table. If an error has a traceback,
    display it as a syntax-highlighted block below the table.
    """
    if data.get("status") == "SUCCESS" and isinstance(data.get("result"), (bytes, bytearray)):
        try:
            data["result"] = deserialize(data["result"])
        except Exception:  # noqa: BLE001
            pass

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    for key in [
        "job_id",
        "status",
        "func_name",        # NEW: show func name in table view
        "args",
        "kwargs",
        "result",
        "error",
        "retries_left",
        "attempts",
        "timeout_policy",   # NEW: show timeout policy
        "created_at",
        "completed_at",
    ]:
        value = data.get(key)
        if key == "error" and value and isinstance(value, dict):
            # Show panel after table
            error_trace = value.get("traceback", "").strip()
            if error_trace:
                table.add_row("error", value.get("message", ""))
                console.print(table)
                console.rule("[red]Traceback[/red]")
                console.print(Syntax(error_trace, "python", theme="monokai", line_numbers=True))
                return
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)
        else:
            value = str(value)

        table.add_row(key, value)

    console.print(table)


# --- NEW helper ------------------------------------------------------------


def _render_raw(data: dict):  # NEW
    """
    Raw mode:
    1. Pretty-print complete JSON metadata.
    2. If an error traceback exists, display it in a Rich syntax block.
    """
    console.rule("[bold green]Job Metadata (raw)[/bold green]")
    console.print_json(data=data)

    err = data.get("error") or {}
    tb = (err.get("traceback") or "").strip()
    if tb:
        console.rule("[bold red]Traceback (raw)[/bold red]")
        console.print(Syntax(tb, "python", theme="monokai", line_numbers=True))
