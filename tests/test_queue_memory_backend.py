import pytest
from nuvom.queue_backends.memory_queue import MemoryJobQueue
from nuvom.job import Job

@pytest.fixture
def memory_queue():
    q = MemoryJobQueue()
    q.clear()  # ensures fresh state
    return q

def test_enqueue_dequeue(memory_queue):
    job = Job(func_name="add", args=(1, 2))
    memory_queue.enqueue(job)
    result = memory_queue.dequeue()
    assert result.func_name == "add"
    assert result.args == (1, 2)

def test_pop_batch(memory_queue):
    jobs = [Job(func_name="f", args=(i,)) for i in range(5)]
    for job in jobs:
        memory_queue.enqueue(job)
    batch = memory_queue.pop_batch(3)
    assert len(batch) == 3

def test_qsize(memory_queue):
    assert memory_queue.qsize() == 0
    memory_queue.enqueue(Job(func_name="noop", args=()))
    assert memory_queue.qsize() == 1
