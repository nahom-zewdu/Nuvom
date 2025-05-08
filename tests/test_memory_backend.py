# tests/test_memory_backend.py

from nuvom.task import task
from nuvom.result_store import get_result, get_error
from nuvom.queue import get_global_queue
from nuvom.result_store import _backend

# Force backend to memory (for isolation)
from nuvom.result_backends.memory_backend import MemoryResultBackend
_backend = MemoryResultBackend()

@task
def add(a, b):
    return a + b

def test_memory_result_backend():
    job = add.delay(2, 3)
    result = job.run()  # run directly
    # Simulate setting result manually
    _backend.set_result(job.id, result)

    assert _backend.get_result(job.id) == 5
    assert _backend.get_error(job.id) is None

if __name__ == "__main__":
    test_memory_result_backend()
    print("✅ test_memory_backend.py passed")
