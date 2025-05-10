import pytest
from nuvom.queue import JobQueue
from nuvom.job import Job
import uuid


def test_enqueue_dequeue_serialized_roundtrip():
    queue = JobQueue()
    job_id = str(uuid.uuid4())
    
    # Create a mock job manually (avoid using Task registry)
    job = Job(
        func_name="mock_task",
        args=(1, 2),
        kwargs={"debug": True},
        retries=2,
        store_result=True
    )
    job.id = job_id  # Force set ID

    queue.enqueue(job)

    # Now dequeue and ensure job is restored
    received = queue.dequeue(timeout=2)

    assert received is not None, "Dequeue returned None"
    assert isinstance(received, Job), "Did not return a Job instance"
    assert received.id == job_id
    assert received.func_name == "mock_task"
    assert received.args == (1, 2)
    assert received.kwargs == {"debug": True}
    assert received.retries_left == 2
    assert received.store_result is True
