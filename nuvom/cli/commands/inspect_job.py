# nuvom/cli/commands/inspect_job.py

import typer
import json
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from typing import Optional

from nuvom.result_store import get_backend
from nuvom.log import logger
from nuvom.serialize import deserialize

inspect_app = typer.Typer(name='inspect', help="Inspect a completed job by ID. Shows full metadata (result, error, args, tracebacks, etc).")
console = Console()

@inspect_app.command("job")
def inspect_job(
    job_id: str,
    format: Optional[str] = typer.Option("table", "--format", "-f", help="Output format: table, json, raw"),
):
    """
    Inspect a completed job by ID. Shows full metadata (result, error, args, tracebacks, etc).
    """
    backend = get_backend()
    metadata = getattr(backend, "get_full", lambda _id: None)(job_id)

    if not metadata:
        console.print(f"[bold red]❌ No metadata found for job:[/bold red] {job_id}")
        raise typer.Exit(code=1)

    if format == "json":
        console.print_json(data=metadata)
    elif format == "raw":
        print(metadata)
    elif format == "table":
        _render_table(metadata)
    else:
        console.print(f"[red]Invalid format:[/red] {format}")
        raise typer.Exit(code=1)

    logger.debug("Inspected job %s with format='%s'", job_id, format)

def _render_table(data: dict):
    if data.get("status") == "SUCCESS" and isinstance(data.get("result"), (bytes, bytearray)):
        try:
            data["result"] = deserialize(data["result"])
        except Exception:  # leave raw if it can’t be decoded
            pass
        
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value", style="")

    for key in [
        "job_id",
        "status",
        "args",
        "kwargs",
        "result",
        "error",
        "retries_left",
        "attempts",
        "created_at",
        "completed_at"
    ]:
        value = data.get(key)
        if key == "error" and value and isinstance(value, dict):
            error_trace = value.get("traceback", "").strip()
            if error_trace:
                syntax = Syntax(error_trace, "python", theme="monokai", line_numbers=True)
                console.print(table)
                console.rule("[red]Traceback[/red]")
                console.print(syntax)
                return
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)
        else:
            value = str(value)

        table.add_row(key, value)

    console.print(table)
