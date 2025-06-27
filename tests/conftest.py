# tests/conftest.py  (replaces the _nuvom_test_safety fixture)

import pytest, threading
from nuvom.queue import clear as clear_queue
from nuvom.registry.registry import get_task_registry
from nuvom.config import override_settings
from nuvom.worker import _shutdown_event

@pytest.fixture(autouse=True)
def nuvom_isolate():
    """
    • Force in-memory back-ends<br>
    • Stop stray worker threads<br>
    • **Do NOT wipe the TaskRegistry at setup** – tasks declared with @task
      in a test module stay registered for that test.<br>
    • Still clean queue + registry **after** each test.
    """
    override_settings(queue_backend="memory", result_backend="memory")

    _shutdown_event.set()
    for t in list(threading.enumerate()):
        if t.name.startswith(("Worker-", "Dispatcher")):
            t.join(timeout=0.5)
    _shutdown_event.clear()

    clear_queue()                    # queue clean
    yield                             # --- test runs here ---

    # teardown: full cleanup for next test
    _shutdown_event.set()
    clear_queue()
    get_task_registry().clear()