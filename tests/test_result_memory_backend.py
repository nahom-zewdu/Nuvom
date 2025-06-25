# tests/test_memory_backend.py

import pytest
from nuvom.result_backends.memory_backend import MemoryResultBackend

@pytest.fixture
def backend():
    return MemoryResultBackend()

def test_success_result_metadata(backend):
    job_id = "job-success"
    result = {"data": 123}
    backend.set_result(job_id, 'test', result, args=[1], kwargs={"x": 2}, retries_left=2, attempts=1)

    assert backend.get_result(job_id) == result
    assert backend.get_error(job_id) is None

    full = backend.get_full(job_id)
    assert full["status"] == "SUCCESS"
    assert full["result"] is not None
    assert full["error"] is None


def test_error_metadata(backend):
    job_id = "job-failed"
    try:
        raise ValueError("boom")
    except ValueError as e:
        backend.set_error(job_id, 'test', e, args=[], kwargs={}, retries_left=0, attempts=1)

    assert backend.get_result(job_id) is None

    error = backend.get_error(job_id)
    assert error["type"] == "ValueError"
    assert "boom" in error["message"]

    full = backend.get_full(job_id)
    assert full["status"] == "FAILED"
    assert full["error"]["type"] == "ValueError"


def test_get_result_missing(backend):
    assert backend.get_result("missing-job") is None


def test_get_error_missing(backend):
    assert backend.get_error("missing-job") is None
