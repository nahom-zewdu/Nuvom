# tests/test_memory_backend.py

import pytest
from nuvom.result_backends.memory_backend import MemoryResultBackend

@pytest.fixture
def backend():
    return MemoryResultBackend()

def test_set_and_get_result(backend):
    job_id = "job-1"
    data = {"foo": "bar"}
    backend.set_result(job_id, data)
    assert backend.get_result(job_id) == data

def test_set_and_get_error(backend):
    job_id = "job-err"
    error_msg = "Something went wrong"
    backend.set_error(job_id, error_msg)
    assert backend.get_error(job_id) == error_msg

def test_get_result_missing(backend):
    assert backend.get_result("missing-job") is None

def test_get_error_missing(backend):
    assert backend.get_error("missing-job") is None
