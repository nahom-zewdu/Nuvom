# nuvom/scheduler/sqlite_store.py

"""
SQLite-backed store for Nuvom Scheduler.
=========================================

This module implements `SchedulerStore` using a local SQLite database. It
persists ScheduledJob definitions and allows CRUD operations.

Key features:
- Thread-safe via `threading.RLock`.
- JSON serialization for complex fields (`args` and `kwargs`).
- Auto-creates table on initialization.
- Compatible with `ScheduledJob` dataclass.
- Minimal external dependencies (only `sqlite3` and `json`).

Usage:
    store = SQLiteStore(db_path="nuvom_scheduler.db")
    job = store.add(scheduled_job_instance)
    jobs = store.list_all()
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import List, Optional

from nuvom.scheduler.model import ScheduledJob
from nuvom.scheduler.store import SchedulerStore
from nuvom.log import get_logger

logger = get_logger()


class SQLiteStore(SchedulerStore):
    """
    SQLite-backed SchedulerStore implementation.

    Attributes
    ----------
    db_path : str
        Path to SQLite database file.
    _conn : sqlite3.Connection
        SQLite connection object.
    _lock : threading.RLock
        Thread-safe lock for concurrent access.
    """

    def __init__(self, db_path: str = "nuvom_scheduler.db") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        """Create `scheduled_jobs` table if it does not exist."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    cron_expr TEXT,
                    interval_secs REAL,
                    run_at REAL,
                    args TEXT,
                    kwargs TEXT,
                    enabled INTEGER NOT NULL,
                    next_run_ts REAL,
                    timezone TEXT,
                    misfire_policy TEXT,
                    concurrency_limit INTEGER,
                    queue_name TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

    # -------------------- CRUD Operations --------------------
    def add(self, job: ScheduledJob) -> ScheduledJob:
        """Persist a new ScheduledJob."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO scheduled_jobs (
                    id, task_name, schedule_type, cron_expr, interval_secs,
                    run_at, args, kwargs, enabled, next_run_ts, timezone,
                    misfire_policy, concurrency_limit, queue_name,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.task_name,
                    job.schedule_type,
                    job.cron_expr,
                    job.interval_secs,
                    job.run_at,
                    json.dumps(job.args),
                    json.dumps(job.kwargs),
                    1 if job.enabled else 0,
                    job.next_run_ts,
                    job.timezone,
                    job.misfire_policy,
                    job.concurrency_limit,
                    job.queue_name,
                    job.created_at,
                    job.updated_at,
                ),
            )
        logger.debug("Added schedule %s to SQLiteStore", job.id)
        return job

    def update(self, job: ScheduledJob) -> ScheduledJob:
        """Update an existing ScheduledJob."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE scheduled_jobs
                SET task_name=?, schedule_type=?, cron_expr=?, interval_secs=?,
                    run_at=?, args=?, kwargs=?, enabled=?, next_run_ts=?,
                    timezone=?, misfire_policy=?, concurrency_limit=?, queue_name=?,
                    created_at=?, updated_at=?
                WHERE id=?
                """,
                (
                    job.task_name,
                    job.schedule_type,
                    job.cron_expr,
                    job.interval_secs,
                    job.run_at,
                    json.dumps(job.args),
                    json.dumps(job.kwargs),
                    1 if job.enabled else 0,
                    job.next_run_ts,
                    job.timezone,
                    job.misfire_policy,
                    job.concurrency_limit,
                    job.queue_name,
                    job.created_at,
                    job.updated_at,
                    job.id,
                ),
            )
        logger.debug("Updated schedule %s in SQLiteStore", job.id)
        return job
        
    def get(self, job_id: str) -> Optional[ScheduledJob]:
        """Retrieve a ScheduledJob by ID."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT * FROM scheduled_jobs WHERE id=?",
                (job_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def list_all(self) -> List[ScheduledJob]:
        """Return all ScheduledJobs."""
        with self._lock, self._conn:
            rows = self._conn.execute("SELECT * FROM scheduled_jobs").fetchall()
            return [self._row_to_job(r) for r in rows]

    def remove(self, job_id: str) -> None:
        """Delete a ScheduledJob by ID."""
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM scheduled_jobs WHERE id=?", (job_id,)
            )
        logger.debug("Removed job %s from SQLiteStore", job_id)

    # -------------------- helpers --------------------
    def _row_to_job(self, row: sqlite3.Row) -> ScheduledJob:
        """Convert a SQLite row to ScheduledJob dataclass."""
        return ScheduledJob(
            id=row["id"],
            task_name=row["task_name"],
            schedule_type=row["schedule_type"],
            cron_expr=row["cron_expr"],
            interval_secs=row["interval_secs"],
            run_at=row["run_at"],
            args=json.loads(row["args"]) if row["args"] else [],
            kwargs=json.loads(row["kwargs"]) if row["kwargs"] else {},
            enabled=bool(row["enabled"]),
            next_run_ts=row["next_run_ts"],
            timezone=row["timezone"],
            misfire_policy=row["misfire_policy"],
            concurrency_limit=row["concurrency_limit"],
            queue_name=row["queue_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
