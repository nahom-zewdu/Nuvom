# tests/test_file_backend.py

import os
import shutil
import pytest

from nuvom.result_backends.file_backend import FileResultBackend

@pytest.fixture
def backend():
    # Use a temp directory for test isolation
    test_dir = "job_results"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    yield FileResultBackend()
    
    shutil.rmtree(test_dir)


def test_success_result_metadata(backend):
    job_id = "file-success"
    result = [1, 2, 3]
    backend.set_result(job_id, result, args=(1,), kwargs={"k": 1}, retries_left=1, attempts=1)

    assert backend.get_result(job_id) == result
    assert backend.get_error(job_id) is None

    full = backend.get_full(job_id)
    assert full["status"] == "SUCCESS"
    assert full["result"] == result
    assert full.get('error', None) is None


def test_error_metadata(backend):
    job_id = "file-failed"
    try:
        raise ValueError("disk gone")
    except Exception as e:
        backend.set_error(job_id, e, args=(4,), kwargs={}, retries_left=0, attempts=1)

    assert backend.get_result(job_id) is None
    assert "disk gone" in backend.get_error(job_id)

    full = backend.get_full(job_id)
    assert full["status"] == "FAILED"
    assert full["error"]["type"] == "ValueError"
    assert full.get('result', None) is None
    


def test_missing_result_returns_none(backend):
    assert backend.get_result("non-existent") is None


def test_missing_error_returns_none(backend):
    assert backend.get_error("non-existent") is None
