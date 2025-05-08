# tests/test_file_backend.py

import os
from nuvom.result_backends.file_backend import FileResultBackend

def test_file_backend():
    backend = FileResultBackend()
    job_id = "test_job_123"
    result = {"hello": "world"}
    error = "Something went wrong"

    backend.set_result(job_id, result)
    assert backend.get_result(job_id) == result

    backend.set_error(job_id, error)
    assert backend.get_error(job_id) == error

    # Clean up
    os.remove(f"job_results/{job_id}.out")
    os.remove(f"job_results/{job_id}.err")

if __name__ == "__main__":
    test_file_backend()
    print("✅ test_file_backend.py passed")
