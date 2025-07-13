# nuvom/queue_backends/sqlite_queue.py

"""
SQLiteJobQueue
~~~~~~~~~~~~~~
A persistent, single-host job queue backend using SQLite.

Key features:
- Durable, lightweight storage of job metadata
- Compatible with `BaseJobQueue` interface
- Visibility timeout support for safe concurrent workers
- Thread-safe access using WAL mode and per-thread connections
- Batch dequeue support via `pop_batch`

Designed for: local task runners, CI agents, offline/desktop job queues

Implements:
- enqueue(job)
- dequeue(timeout=1)
- pop_batch(batch_size=1, timeout=1)
- qsize()
- clear()

Stores: serialized `job.to_dict()` using msgpack
"""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, List

from nuvom.job import Job
from nuvom.queue_backends.base import BaseJobQueue
from nuvom.serialize import serialize, deserialize
from nuvom.log import get_logger
from nuvom.plugins.contracts import API_VERSION

logger = get_logger()
_SQLITE_LOCAL = threading.local()


class SQLiteJobQueue(BaseJobQueue):
    """
    SQLite-backed job queue implementation.

    Jobs are stored in a local database file (`queue.db` by default) and dequeued
    safely using a visibility timeout model. This backend is ideal for durable,
    concurrent-safe queuing without requiring a separate service.
    """
    
    api_version = API_VERSION
    name = "sqlite"
    provides = ["queue_backend"]
    requires: list[str] = []

    def __init__(self, db_path: str = ".nuvom/queue.db", visibility_timeout: int = 10):
        """
        Initialize the SQLite job queue.

        Args:
            db_path (str): Path to the SQLite database file.
            visibility_timeout (int): Seconds before a dequeued job becomes visible again
                                      if not acknowledged. Default is 10.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.visibility_timeout = visibility_timeout
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Return thread-local SQLite connection in WAL mode."""
        if not hasattr(_SQLITE_LOCAL, "conn"):
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
            _SQLITE_LOCAL.conn = conn
        return _SQLITE_LOCAL.conn

    def _init_db(self):
        """Create jobs table if not exists."""
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queue_jobs (
                id TEXT PRIMARY KEY,
                payload BLOB NOT NULL,
                status TEXT NOT NULL,
                created_at REAL,
                claimed_at REAL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON queue_jobs(status);")
        conn.commit()

    def enqueue(self, job: Job) -> None:
        """
        Add a new job to the queue.

        Args:
            job (Job): Job instance to queue.
        """
        conn = self._get_conn()
        payload = serialize(job.to_dict())
        conn.execute(
            """
            INSERT OR REPLACE INTO queue_jobs (id, payload, status, created_at, claimed_at)
            VALUES (?, ?, 'READY', ?, NULL);
            """,
            (job.id, payload, job.created_at),
        )
        conn.commit()
        logger.info(f"[sqlite-queue] Enqueued job {job.id}")

    def dequeue(self, timeout: int = 1) -> Optional[Job]:
        """
        Claim a job for execution, respecting visibility timeout.

        Args:
            timeout (int): Unused (reserved for interface compatibility).

        Returns:
            Optional[Job]: A claimed job or None if none available.
        """
        conn = self._get_conn()
        now = time.time()
        stale_cutoff = now - self.visibility_timeout

        # Try to claim a READY or expired CLAIMED job
        row = conn.execute(
            """
            SELECT * FROM queue_jobs
            WHERE status IN ('READY', 'CLAIMED')
              AND (claimed_at IS NULL OR claimed_at < ?)
            ORDER BY created_at ASC
            LIMIT 1;
            """,
            (stale_cutoff,)
        ).fetchone()

        if not row:
            return None

        conn.execute(
            """
            UPDATE queue_jobs SET status = 'CLAIMED', claimed_at = ? WHERE id = ?;
            """,
            (now, row["id"]),
        )
        conn.commit()

        job = Job.from_dict(deserialize(row["payload"]))
        logger.info(f"[sqlite-queue] Claimed job {job.id}")
        return job

    def pop_batch(self, batch_size: int = 1, timeout: int = 1) -> List[Job]:
        """
        Claim up to `batch_size` jobs atomically.

        Args:
            batch_size (int): Number of jobs to dequeue.
            timeout (int): Unused.

        Returns:
            List[Job]: List of claimed jobs.
        """
        jobs = []
        now = time.time()
        stale_cutoff = now - self.visibility_timeout
        conn = self._get_conn()

        rows = conn.execute(
            f"""
            SELECT * FROM queue_jobs
            WHERE status IN ('READY', 'CLAIMED')
              AND (claimed_at IS NULL OR claimed_at < ?)
            ORDER BY created_at ASC
            LIMIT ?;
            """,
            (stale_cutoff, batch_size),
        ).fetchall()

        for row in rows:
            conn.execute(
                "UPDATE queue_jobs SET status = 'CLAIMED', claimed_at = ? WHERE id = ?;",
                (now, row["id"]),
            )
            jobs.append(Job.from_dict(deserialize(row["payload"])))

        conn.commit()
        return jobs

    def qsize(self) -> int:
        """
        Return the number of jobs currently in the queue.

        Returns:
            int: Count of jobs not marked as DONE.
        """
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) FROM queue_jobs WHERE status != 'DONE';").fetchone()[0]

    def clear(self) -> int:
        """
        Remove all jobs from the queue.

        Returns:
            int: Number of jobs deleted.
        """
        conn = self._get_conn()
        deleted = conn.execute("DELETE FROM queue_jobs;").rowcount
        conn.commit()
        return deleted
    
    def mark_done(self, job_id: str) -> None:
        """
        Mark a job as DONE.

        Args:
            job_id (str): ID of the job to mark as DONE.
        """
        
        conn = self._get_conn()
        conn.execute(
            "UPDATE queue_jobs SET status = 'DONE' WHERE id = ?;",
            (job_id,)
        )
        conn.commit()

