# tests/test_queue_sqlite_backend.py

import time
import uuid
import pytest

from nuvom.job import Job
from nuvom.queue_backends.sqlite_queue import SQLiteJobQueue


@pytest.fixture()
def sqlite_queue(tmp_path):
    """
    Provides a fresh SQLiteJobQueue instance with a temporary database.
    Ensures each test gets an isolated, clean database.
    """
    db_file = tmp_path / "queue.db"
    queue = SQLiteJobQueue(str(db_file), visibility_timeout=1)
    yield queue
    queue.clear()


def make_job(*, args=None, kwargs=None, **extra) -> Job:
    return Job(
        func_name="dummy",
        args=args or [1, 2],
        kwargs=kwargs or {},
        retries=1,
        store_result=True,
        **extra,
    )



def test_enqueue_and_dequeue(sqlite_queue):
    """
    Tests that a job can be enqueued and then successfully dequeued,
    and that queue size reflects job state transitions.
    """
    job = make_job()
    sqlite_queue.enqueue(job)

    assert sqlite_queue.qsize() == 1

    claimed = sqlite_queue.dequeue()
    assert claimed.id == job.id
    assert sqlite_queue.qsize() == 1  # Claimed but not done

    sqlite_queue.mark_done(job.id)
    assert sqlite_queue.qsize() == 0


def test_pop_batch(sqlite_queue):
    """
    Tests batch dequeueing functionality, ensuring batch size is respected
    and that marking jobs as done reduces the queue size correctly.
    """
    jobs = [make_job() for _ in range(5)]
    for job in jobs:
        sqlite_queue.enqueue(job)

    batch = sqlite_queue.pop_batch(batch_size=3)
    assert len(batch) == 3
    remaining = sqlite_queue.qsize()
    assert remaining == 5  # still in queue, just claimed

    for job in batch:
        sqlite_queue.mark_done(job.id)

    assert sqlite_queue.qsize() == 2


def test_visibility_timeout(sqlite_queue):
    """
    Verifies that a claimed job is not immediately dequeued again,
    but becomes available after the visibility timeout expires.
    """
    job = make_job()
    sqlite_queue.enqueue(job)

    first = sqlite_queue.dequeue()
    assert first is not None
    assert first.id == job.id

    second = sqlite_queue.dequeue()
    assert second is None  # still within visibility window

    time.sleep(1.1)

    third = sqlite_queue.dequeue()
    assert third is not None
    assert third.id == job.id


def test_clear(sqlite_queue):
    """
    Tests that calling clear removes all jobs from the queue.
    """
    for _ in range(3):
        sqlite_queue.enqueue(make_job())
    assert sqlite_queue.qsize() == 3
    removed = sqlite_queue.clear()
    assert removed == 3
    assert sqlite_queue.qsize() == 0


def test_reenqueue_after_claim_expiry(sqlite_queue):
    """
    Verifies that jobs not marked as done after being claimed
    are re-enqueued after the visibility timeout.
    """
    job = make_job()
    sqlite_queue.enqueue(job)
    sqlite_queue.dequeue()  # claimed but not marked done

    time.sleep(1.1)  # wait for visibility timeout

    # should become available again
    job2 = sqlite_queue.dequeue()
    assert job2 is not None
    assert job2.id == job.id

def test_concurrent_batch_claiming(sqlite_queue):
    """
    Simulates concurrent-like batch claiming to ensure no duplicate jobs
    are dequeued and proper accounting of queue state is maintained.
    """
    for _ in range(10):
        sqlite_queue.enqueue(make_job())

    b1 = sqlite_queue.pop_batch(5)
    b2 = sqlite_queue.pop_batch(5)

    all_ids = [j.id for j in b1 + b2]
    assert len(all_ids) == len(set(all_ids))  # no duplicates

    # All are still technically "in queue" unless marked done
    assert sqlite_queue.qsize() == 10

    for j in b1 + b2:
        sqlite_queue.mark_done(j.id)

    assert sqlite_queue.qsize() == 0

