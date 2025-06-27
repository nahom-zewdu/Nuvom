# tests/test_result_sqlite_backend.py

"""
End-to-end tests for SQLiteResultBackend.

These tests run against a temporary DB file so they are 100 % isolated.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from nuvom.result_backends.sqlite_backend import SQLiteResultBackend


@pytest.fixture()
def backend(tmp_path: Path):
    """Return a fresh SQLite backend using a tmp file."""
    db_file = tmp_path / "nuvom_test.db"
    return SQLiteResultBackend(db_file)


def _insert_success(backend: SQLiteResultBackend, job_id="job-success"):
    backend.set_result(
        job_id=job_id,
        func_name="add",
        result=42,
        args=(40, 2),
        kwargs={},
        retries_left=0,
        attempts=1,
        created_at=time.time() - 1,
        completed_at=time.time(),
    )
    return job_id


def _insert_failure(backend: SQLiteResultBackend, job_id="job-fail"):
    backend.set_error(
        job_id=job_id,
        func_name="explode",
        error=ValueError("boom"),
        args=(),
        kwargs={},
        retries_left=0,
        attempts=1,
        created_at=time.time() - 1,
        completed_at=time.time(),
    )
    return job_id


# ──────────────────────────────────────────────────────────────────────────
# CRUD Tests
# ──────────────────────────────────────────────────────────────────────────
def test_set_and_get_result(backend):
    jid = _insert_success(backend)
    assert backend.get_result(jid) == 42
    assert backend.get_error(jid) is None


def test_set_and_get_error(backend):
    jid = _insert_failure(backend)
    err = backend.get_error(jid)
    assert "boom" in err
    assert backend.get_result(jid) is None


def test_get_full_metadata_success(backend):
    jid = _insert_success(backend)
    meta = backend.get_full(jid)
    assert meta["status"] == "SUCCESS"
    assert meta["func_name"] == "add"
    assert meta["result"] == 42
    assert meta["error_msg"] is None


def test_get_full_metadata_failure(backend):
    jid = _insert_failure(backend)
    meta = backend.get_full(jid)
    assert meta["status"] == "FAILED"
    assert meta["func_name"] == "explode"
    assert "boom" in meta["error_msg"]


def test_list_jobs_returns_ordered(backend):
    s1 = _insert_success(backend, "A")
    time.sleep(0.01)
    f1 = _insert_failure(backend, "B")

    jobs = backend.list_jobs()
    # Most recent first
    assert jobs[0]["job_id"] == f1
    assert jobs[1]["job_id"] == s1

    # Round-trip: ensure deserialized blobs are usable
    assert jobs[1]["args"] == [40, 2]
