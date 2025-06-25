# nuvom/cli/commands/runtestworker.py

"""
Dev-only synchronous worker: execute a single job JSON payload locally.

Example:
    nuvom runtestworker ./job.json
"""

import json
import sys
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from nuvom.job import Job
from nuvom.log import logger

runtest_app = typer.Typer(help="Run a single job JSON deterministically (CI/dev)")

console = Console()


@runtest_app.command("run")
def runtestworker(
    job_file: Path = typer.Argument(..., exists=True, readable=True, help="Path to JSON file describing the job")
):
    """
    Execute one job synchronously. Exit-code 0 on success, 1 on failure.
    """
    try:
        payload = json.loads(job_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(Panel(str(exc), title="Invalid JSON", style="red"))
        sys.exit(1)

    # Required fields
    func_name = payload.get("func_name")
    if not func_name:
        console.print(Panel("Missing 'func_name' field", style="red"))
        sys.exit(1)

    job = Job(
        func_name=func_name,
        args=payload.get("args", []),
        kwargs=payload.get("kwargs", {}),
        store_result=False,        # keep completely local
        timeout_secs=payload.get("timeout_secs"),
        retries=payload.get("retries", 0),
    )

    logger.info("[TestWorker] Running %s with args=%s kwargs=%s", func_name, job.args, job.kwargs)

    try:
        result = job.run()
        console.print(Panel(f"[bold green]Result:[/bold green] {result}", title="SUCCESS", style="green"))
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        console.print(Panel(f"[bold red]{type(exc).__name__}[/bold red]: {exc}", title="FAILED", style="red"))
        logger.exception("TestWorker failed")
        sys.exit(1)
