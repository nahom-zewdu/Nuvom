# tests/test_file_backend.py

import os
import shutil
import pytest

from nuvom.result_backends.file_backend import FileResultBackend

@pytest.fixture
def backend():
    # Set up a clean directory before each test
    test_dir = "job_results"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)

    yield FileResultBackend()

    # Cleanup
    shutil.rmtree(test_dir)

def test_set_and_get_result(backend):
    job_id = "job-1"
    data = {"value": 42}
    backend.set_result(job_id, data)
    assert backend.get_result(job_id) == data

def test_set_and_get_error(backend):
    job_id = "err-1"
    error = "Failure reason"
    backend.set_error(job_id, error)
    assert backend.get_error(job_id) == error

def test_missing_result_returns_none(backend):
    assert backend.get_result("non-existent") is None

def test_missing_error_returns_none(backend):
    assert backend.get_error("non-existent") is None
