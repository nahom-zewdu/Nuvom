# nuvom/scheduler/decorators.py

"""
Scheduled task decorator for Nuvom
==================================

This module provides a decorator to mark Python functions as scheduled tasks.
It integrates with AST-based task discovery and is fully compatible with
ScheduledJob metadata and the Scheduler engine.

Key features:
- Attach scheduling metadata (cron, interval, once) to functions.
- Supports arguments, kwargs, misfire policy, concurrency limit, queue selection.
- Does not auto-register at import; discovery system picks up decorated functions.
"""

from __future__ import annotations
from typing import Any, Callable, Literal, Optional, List, Dict
from functools import wraps

from nuvom.scheduler.model import ScheduledJob


def scheduled_task(
    *,
    schedule_type: Literal["cron", "interval", "once"],
    cron_expr: Optional[str] = None,
    interval_secs: Optional[int] = None,
    run_at: Optional[float] = None,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
    misfire_policy: Literal["run_immediately", "skip", "reschedule"] = "run_immediately",
    concurrency_limit: Optional[int] = None,
    queue_name: Optional[str] = None,
    timezone: Optional[str] = "UTC",
) -> Callable:
    """
    Decorator to mark a Python function as a scheduled task.

    This decorator does not register the task for execution immediately.
    AST-based task discovery reads this metadata to populate the task registry
    and the scheduler store.

    Parameters
    ----------
    schedule_type : Literal["cron", "interval", "once"]
        Type of schedule.
    cron_expr : Optional[str]
        Cron expression (required if schedule_type == "cron").
    interval_secs : Optional[int]
        Interval in seconds (required if schedule_type == "interval").
    run_at : Optional[float]
        Unix timestamp for one-off schedules (required if schedule_type == "once").
    args : Optional[List[Any]]
        Default positional arguments for the task.
    kwargs : Optional[Dict[str, Any]]
        Default keyword arguments for the task.
    enabled : bool
        Whether the schedule should be active on startup.
    misfire_policy : Literal['run_immediately','skip','reschedule']
        Behavior for missed runs.
    concurrency_limit : Optional[int]
        Maximum concurrent jobs for this schedule.
    queue_name : Optional[str]
        Optional queue target.
    timezone : Optional[str]
        Timezone for cron evaluation (IANA format).

    Usage
    -----
        @scheduled_task(schedule_type="cron", cron_expr="0 0 * * *")
        def my_task():
            ...

    Returns
    -------
    Callable
        The original function, wrapped with `_scheduled_metadata` attached.
    """

    def decorator(func: Callable) -> Callable:
        metadata = {
            "schedule_type": schedule_type,
            "cron_expr": cron_expr,
            "interval_secs": interval_secs,
            "run_at": run_at,
            "args": args or [],
            "kwargs": kwargs or {},
            "enabled": enabled,
            "misfire_policy": misfire_policy,
            "concurrency_limit": concurrency_limit,
            "queue_name": queue_name,
            "timezone": timezone,
            "task_name": func.__name__,
        }
        # Attach metadata to the function for AST discovery
        setattr(func, "_scheduled_metadata", metadata)

        @wraps(func)
        def wrapped(*f_args, **f_kwargs):
            return func(*f_args, **f_kwargs)

        return wrapped

    return decorator
