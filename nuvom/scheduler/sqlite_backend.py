# nuvom/scheduler/sqlite_backend.py

"""
SQLite Scheduler Backend
========================

Durable scheduler backend using SQLite.

- Stores `ScheduleEnvelope` records for persistence and recovery.
- Implements all `SchedulerBackend` methods.
- Compatible with dispatcher and worker loops.

This implementation is:
- Lightweight (single file, no extra deps)
- Thread-safe for basic concurrent use
- Ready for extension to Postgres/MySQL in production

Author: Nuvom Scheduler Team
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from nuvom.log import get_logger
from nuvom.scheduler.backend import SchedulerBackend
from nuvom.scheduler.models import ScheduledTaskReference, ScheduleEnvelope

logger = get_logger()


class SqlSchedulerBackend(SchedulerBackend):
    """
    SQLite-based backend for durable schedule storage.
    """

    def __init__(self, db_path: str = ".nuvom/scheduler.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._setup_schema()
        logger.info("[scheduler.sql] Using SQLite backend at %s", self.db_path)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _setup_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                args TEXT,
                kwargs TEXT,
                schedule_type TEXT NOT NULL,
                next_run_ts REAL,
                interval_secs INTEGER,
                cron_expr TEXT,
                timezone TEXT,
                priority INTEGER,
                metadata TEXT,
                status TEXT,
                run_count INTEGER,
                created_at REAL,
                updated_at REAL
            )
            """
        )
        self._conn.commit()

    def _row_to_envelope(self, row: sqlite3.Row) -> ScheduleEnvelope:
        return ScheduleEnvelope(
            id=row["id"],
            task_name=row["task_name"],
            args=json.loads(row["args"]),
            kwargs=json.loads(row["kwargs"]),
            schedule_type=row["schedule_type"],
            next_run_ts=row["next_run_ts"],
            interval_secs=row["interval_secs"],
            cron_expr=row["cron_expr"],
            timezone=row["timezone"],
            priority=row["priority"],
            metadata=json.loads(row["metadata"]),
            status=row["status"],
            run_count=row["run_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _envelope_to_db_row(self, env: ScheduleEnvelope) -> tuple:
        return (
            env.id,
            env.task_name,
            json.dumps(env.args),
            json.dumps(env.kwargs),
            env.schedule_type,
            env.next_run_ts,
            env.interval_secs,
            env.cron_expr,
            env.timezone,
            env.priority,
            json.dumps(env.metadata),
            env.status,
            env.run_count,
            env.created_at,
            env.updated_at,
        )

    # ------------------------------------------------------------------ #
    # Interface implementation
    # ------------------------------------------------------------------ #
    def enqueue(self, ref: ScheduledTaskReference) -> ScheduleEnvelope:
        envelope = ref.to_envelope()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO schedules
            (id, task_name, args, kwargs, schedule_type, next_run_ts,
             interval_secs, cron_expr, timezone, priority, metadata,
             status, run_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._envelope_to_db_row(envelope),
        )
        self._conn.commit()
        logger.debug("[scheduler.sql] Enqueued schedule %s", envelope.id)
        return envelope

    def get(self, schedule_id: str) -> Optional[ScheduleEnvelope]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
        row = cur.fetchone()
        return self._row_to_envelope(row) if row else None

    def list(self) -> List[ScheduleEnvelope]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM schedules ORDER BY next_run_ts ASC")
        rows = cur.fetchall()
        return [self._row_to_envelope(row) for row in rows]

    def due(self, now_ts: Optional[float] = None, limit: Optional[int] = None) -> List[ScheduleEnvelope]:
        now_ts = now_ts or time.time()
        sql = """
            SELECT * FROM schedules
            WHERE status = 'pending' AND next_run_ts IS NOT NULL AND next_run_ts <= ?
            ORDER BY next_run_ts ASC
        """
        if limit:
            sql += f" LIMIT {limit}"
        cur = self._conn.cursor()
        cur.execute(sql, (now_ts,))
        rows = cur.fetchall()
        return [self._row_to_envelope(row) for row in rows]

    def ack_dispatched(self, schedule_id: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE schedules
            SET status = 'dispatched',
                run_count = run_count + 1,
                updated_at = ?
            WHERE id = ?
            """,
            (time.time(), schedule_id),
        )
        self._conn.commit()
        logger.debug("[scheduler.sql] Ack dispatched schedule %s", schedule_id)

    def reschedule(self, schedule_id: str, next_run_ts: float) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE schedules
            SET next_run_ts = ?, status = 'pending', updated_at = ?
            WHERE id = ?
            """,
            (next_run_ts, time.time(), schedule_id),
        )
        self._conn.commit()
        logger.debug("[scheduler.sql] Rescheduled %s -> %s", schedule_id, next_run_ts)

    def cancel(self, schedule_id: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE schedules SET status = 'cancelled', updated_at = ? WHERE id = ?",
            (time.time(), schedule_id),
        )
        self._conn.commit()
        logger.debug("[scheduler.sql] Cancelled schedule %s", schedule_id)

    def close(self) -> None:
        self._conn.close()
        logger.info("[scheduler.sql] Closed SQLite backend")
