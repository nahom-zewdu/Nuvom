# nuvom/cli/commands/runtestworker.py

"""
Dev-only synchronous worker: execute a single job JSON payload locally.

Example:
    nuvom runtestworker run ./job.json
"""

import json
import sys
import importlib.util
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from nuvom.job import Job
from nuvom.log import logger
from nuvom.registry.auto_register import auto_register_from_manifest

runtest_app = typer.Typer(
    help="Run a single job JSON deterministically (CI / local dev)"
)

console = Console()


@runtest_app.command("run")
def runtestworker(
    job_file: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path to JSON file describing the job",
    ),
    task_module: Path = typer.Option(
        None,
        "--task-module",
        exists=True,
        readable=True,
        help="Optional path to a .py file containing @task-decorated functions "
        "that should be imported before running the job",
    ),
) -> None:
    """
    Execute one job synchronously.

    • Exit-code **0**  → success  
    • Exit-code **1**  → failure (exception)  
    """

    # ── Load JSON payload ───────────────────────────────────────────────
    try:
        payload = json.loads(job_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(Panel(str(exc), title="Invalid JSON", style="red"))
        sys.exit(1)

    func_name: str | None = payload.get("func_name")
    if not func_name:
        console.print(Panel("Missing 'func_name' field", style="red"))
        sys.exit(1)

    # ── Optional: dynamically import the supplied task module ───────────
    if task_module is not None:
        spec = importlib.util.spec_from_file_location(task_module.stem, task_module)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod                             # type: ignore[arg-type]
            spec.loader.exec_module(mod)                             # type: ignore[attr-defined]
            logger.debug("[TestWorker] Imported task module %s", task_module)
        else:
            console.print(
                Panel(f"Could not import task module: {task_module}", style="red")
            )
            sys.exit(1)
    else:
        # Fallback to manifest-based auto-registration
        auto_register_from_manifest()

    # ── Build the Job object ────────────────────────────────────────────
    job = Job(
        func_name=func_name,
        args=payload.get("args", []),
        kwargs=payload.get("kwargs", {}),
        store_result=False,  # purely local; no backend persistence
        timeout_secs=payload.get("timeout_secs"),
        retries=payload.get("retries", 0),
    )

    logger.info(
        "[TestWorker] Running %s with args=%s kwargs=%s",
        func_name,
        job.args,
        job.kwargs,
    )

    # ── Execute and report ──────────────────────────────────────────────
    try:
        result = job.run()
        console.print(
            Panel(
                f"[bold green]Result:[/bold green] {result}",
                title="SUCCESS",
                style="green",
            )
        )
        sys.exit(0)

    except Exception as exc:  # noqa: BLE001
        console.print(
            Panel(
                f"[bold red]{type(exc).__name__}[/bold red]: {exc}",
                title="FAILED",
                style="red",
            )
        )
        logger.exception("TestWorker failed")
        sys.exit(1)
