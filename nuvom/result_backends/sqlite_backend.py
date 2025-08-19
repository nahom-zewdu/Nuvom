# nuvom/result_backend/sqlite_backend.py

"""
SQLiteResultBackend
~~~~~~~~~~~~~~~~~~~

Durable, zero-infra result backend that stores all job metadata in a single
SQLite database file (default: ``.nuvom/nuvom.db``).

Key design goals
----------------
* Full parity with Memory/File backends (`get_result`, `get_error`, `get_full`,
  `list_jobs`)
* Safe for concurrent threaded access (single connection per thread via
  `sqlite3.Connection` + WAL mode)
* Uses msgpack to store `args`, `kwargs`, and `result` blobs
* Job priority (integer, lower = higher priority)
* Scheduled flag (boolean)
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional, Dict, List
import traceback

from nuvom.serialize import serialize, deserialize
from nuvom.result_backends.base import BaseResultBackend
from nuvom.log import get_logger
from nuvom.plugins.contracts import Plugin, API_VERSION

logger = get_logger()
_SQLITE_THREAD_LOCAL = threading.local()



def _get_connection(db_path: Path) -> sqlite3.Connection:
    """
    Return a thread-local SQLite connection (WAL mode, autocommit).
    Initializes schema if needed.
    """
    if not hasattr(_SQLITE_THREAD_LOCAL, "conn"):
        conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        _SQLITE_THREAD_LOCAL.conn = conn

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id        TEXT PRIMARY KEY,
                func_name     TEXT,
                args          BLOB,
                kwargs        BLOB,
                status        TEXT,
                result        BLOB,
                error_type    TEXT,
                error_msg     TEXT,
                traceback     TEXT,
                attempts      INTEGER,
                retries_left  INTEGER,
                timeout_secs  INTEGER,
                created_at    REAL,
                completed_at  REAL,
                priority      INTEGER DEFAULT 5,
                scheduled     INTEGER DEFAULT 0
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_status_created_priority "
            "ON jobs (status, priority ASC, created_at ASC);"
        )
    return _SQLITE_THREAD_LOCAL.conn  # type: ignore[attr-defined]


class SQLiteResultBackend(BaseResultBackend):
    """SQLite-based backend storing every job in a single `jobs` table."""

    api_version = API_VERSION
    name = "sqlite"
    provides = ["result_backend"]
    requires: list[str] = []

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or ".nuvom/nuvom.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def start(self, settings: dict): ...
    def stop(self): ...

    def set_result(
        self,
        job_id: str,
        func_name: str,
        result: Any,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
        priority: int = 5,
        scheduled: bool = False,
        timeout_secs: Optional[int] = None,
    ) -> None:
        conn = _get_connection(self.db_path)
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, func_name, args, kwargs,
                status, result, attempts, retries_left,
                created_at, completed_at, priority, scheduled, timeout_secs
            ) VALUES (
                :job_id, :func_name, :args, :kwargs,
                'SUCCESS', :result, :attempts, :retries_left,
                :created_at, :completed_at, :priority, :scheduled, :timeout_secs
            )
            ON CONFLICT(job_id) DO UPDATE SET
                func_name    = excluded.func_name,
                args         = excluded.args,
                kwargs       = excluded.kwargs,
                status       = 'SUCCESS',
                result       = excluded.result,
                attempts     = excluded.attempts,
                retries_left = excluded.retries_left,
                completed_at = excluded.completed_at,
                priority     = excluded.priority,
                scheduled    = excluded.scheduled,
                timeout_secs = excluded.timeout_secs;
            """,
            {
                "job_id": job_id,
                "func_name": func_name,
                "args": serialize(args or ()),
                "kwargs": serialize(kwargs or {}),
                "result": serialize(result),
                "attempts": attempts,
                "retries_left": retries_left,
                "created_at": created_at or time.time(),
                "completed_at": completed_at or time.time(),
                "priority": priority,
                "scheduled": int(scheduled),
                "timeout_secs": timeout_secs,
            },
        )
        conn.commit()

    def set_error(
        self,
        job_id: str,
        func_name: str,
        error: Exception,
        *,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
        priority: int = 5,
        scheduled: bool = False,
        timeout_secs: Optional[int] = None,
    ) -> None:
        conn = _get_connection(self.db_path)
        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, func_name, args, kwargs,
                status, error_type, error_msg, traceback,
                attempts, retries_left, created_at, completed_at,
                priority, scheduled, timeout_secs
            ) VALUES (
                :job_id, :func_name, :args, :kwargs,
                'FAILED', :etype, :emsg, :tb,
                :attempts, :retries_left, :created_at, :completed_at,
                :priority, :scheduled, :timeout_secs
            )
            ON CONFLICT(job_id) DO UPDATE SET
                func_name    = excluded.func_name,
                args         = excluded.args,
                kwargs       = excluded.kwargs,
                status       = 'FAILED',
                error_type   = excluded.error_type,
                error_msg    = excluded.error_msg,
                traceback    = excluded.traceback,
                attempts     = excluded.attempts,
                retries_left = excluded.retries_left,
                completed_at = excluded.completed_at,
                priority     = excluded.priority,
                scheduled    = excluded.scheduled,
                timeout_secs = excluded.timeout_secs;
            """,
            {
                "job_id": job_id,
                "func_name": func_name,
                "args": serialize(args or ()),
                "kwargs": serialize(kwargs or {}),
                "etype": type(error).__name__,
                "emsg": str(error),
                "tb": tb_str,
                "attempts": attempts,
                "retries_left": retries_left,
                "created_at": created_at or time.time(),
                "completed_at": completed_at or time.time(),
                "priority": priority,
                "scheduled": int(scheduled),
                "timeout_secs": timeout_secs,
            },
        )
        conn.commit()

    def get_full(self, job_id: str) -> Optional[Dict]:
        row = _get_connection(self.db_path).execute(
            "SELECT * FROM jobs WHERE job_id=?;", (job_id,)
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["args"] = deserialize(data["args"])
        data["kwargs"] = deserialize(data["kwargs"])
        if data.get("result") is not None:
            data["result"] = deserialize(data["result"])
        data["scheduled"] = bool(data.get("scheduled", 0))
        return data

    def list_jobs(self, order_by_priority: bool = False) -> List[Dict]:
        """
        List all jobs.

        Parameters
        ----------
        order_by_priority : bool
            If True, jobs are sorted by priority ASC, created_at ASC.
        """
        conn = _get_connection(self.db_path)
        query = "SELECT * FROM jobs"
        if order_by_priority:
            query += " ORDER BY priority ASC, created_at ASC"
        else:
            query += " ORDER BY created_at DESC"
        rows = conn.execute(query).fetchall()

        output = []
        for r in rows:
            record = dict(r)
            record["args"] = deserialize(record["args"])
            record["kwargs"] = deserialize(record["kwargs"])
            if record.get("result") is not None:
                record["result"] = deserialize(record["result"])
            record["scheduled"] = bool(record.get("scheduled", 0))
            output.append(record)
        return output

    def get_result(self, job_id: str) -> Any | None:
        row = _get_connection(self.db_path).execute(
            "SELECT result FROM jobs WHERE job_id=? AND status='SUCCESS';", (job_id,)
        ).fetchone()
        return deserialize(row["result"]) if row and row["result"] is not None else None

    def get_error(self, job_id: str) -> Optional[str]:
        row = _get_connection(self.db_path).execute(
            "SELECT error_msg FROM jobs WHERE job_id=? AND status='FAILED';", (job_id,)
        ).fetchone()
        return row["error_msg"] if row and row["error_msg"] else None
