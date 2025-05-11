import shutil
import os
import pytest

from nuvom.queue_backends.file_queue import FileJobQueue
from nuvom.job import Job

@pytest.fixture
def file_queue(tmp_path):
    dir_path = tmp_path / "queue_dir"
    q = FileJobQueue(directory=str(dir_path))
    q.clear()
    yield q
    shutil.rmtree(str(dir_path))  # cleanup after test

def test_enqueue_dequeue_file(file_queue):
    job = Job(func_name="mul", args=(3, 4))
    file_queue.enqueue(job)
    result = file_queue.dequeue()
    assert result.func_name == "mul"
    assert result.args == (3, 4)

def test_batch_ordering(file_queue):
    jobs = [Job(func_name="f", args=(i,)) for i in range(10)]
    for job in jobs:
        file_queue.enqueue(job)

    batch = file_queue.pop_batch(5)
    assert len(batch) == 5
    assert [j.args[0] for j in batch] == list(range(5))

def test_qsize_file(file_queue):
    file_queue.enqueue(Job(func_name="noop", args=()))
    file_queue.enqueue(Job(func_name="noop", args=()))
    assert file_queue.qsize() == 2

def test_corrupt_file_skipped(file_queue):
    # Create an invalid job file
    path = file_queue._job_path("corrupt")
    with open(path, "wb") as f:
        f.write(b"invalid data")

    job = Job(func_name="valid", args=(1,))
    file_queue.enqueue(job)

    result = file_queue.dequeue()
    assert result.func_name == "valid"
