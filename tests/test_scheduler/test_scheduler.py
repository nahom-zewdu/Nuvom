# tests/test_scheduler/test_scheduler.py

import time
import pytest
from nuvom.scheduler import get_scheduler_backend, ScheduledTaskReference
from nuvom.scheduler.memory_backend import InMemorySchedulerBackend
from nuvom.scheduler.dispatcher import dispatch_once
from nuvom.queue import dequeue


@pytest.fixture
def memory_backend():
    backend = InMemorySchedulerBackend()
    # ensure clean slate before each test
    backend._clear()
    yield backend
    # clear again after test
    backend._clear()


def test_enqueue_and_due(memory_backend):
    backend = memory_backend
    ref = ScheduledTaskReference.create(
        func_name="tests.dummy_task",
        args=[1, 2],
        kwargs={},
        schedule_type="one_off",
        next_run=time.time()
    )

    env = backend.enqueue(ref)
    assert env.id
    assert env.task_name == "tests.dummy_task"

    due_items = backend.due(now_ts=time.time() + 1)
    assert len(due_items) == 1
    assert due_items[0].id == env.id


def test_dispatch_once_for_one_off(memory_backend, monkeypatch):
    monkeypatch.setattr("nuvom.scheduler.get_scheduler_backend", lambda: memory_backend)
    backend = memory_backend

    ref = ScheduledTaskReference.create(
        func_name="tests.dummy_task",
        args=[5, 7],
        schedule_type="one_off",
        next_run=time.time()
    )
    env = backend.enqueue(ref)

    count = dispatch_once(backend=backend)
    assert count == 1

    # The backend should mark the schedule as cancelled after dispatch
    env_after = backend.get(env.id)
    assert env_after is not None
    assert env_after.status == "cancelled"


def test_dispatch_interval_reschedule(memory_backend):
    backend = memory_backend

    ref = ScheduledTaskReference.create(
        func_name="tests.dummy_task",
        args=[1],
        schedule_type="interval",
        next_run=time.time(),
        interval_secs=1
    )
    env = backend.enqueue(ref)
    first_ts = env.next_run_ts

    count = dispatch_once(backend=backend)
    assert count == 1

    # Should reschedule instead of cancel
    updated = backend.get(env.id)
    assert updated is not None
    assert updated.next_run_ts > first_ts


def test_singleton_is_threadsafe(memory_backend):
    import threading
    results = []

    def worker():
        results.append(memory_backend)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    # all returned objects should be the same singleton
    assert all(r is results[0] for r in results)
