# tests/conftest.py  (only the parts that changed)

import importlib
import threading
import pytest

from nuvom.config import override_settings
from nuvom.queue import clear as clear_queue, reset_backend as reset_q_backend
from nuvom.result_store import reset_backend as reset_result_backend
from nuvom.registry.registry import get_task_registry
from nuvom.worker import _shutdown_event
from nuvom.plugins import loader as plugload, registry as plugreg
import nuvom.queue as nuvo_queue


@pytest.fixture(autouse=True)
def nuvom_isolate():
    # ── SET‑UP ──────────────────────────────────────────────────────────
    override_settings(queue_backend="memory", result_backend="memory")
    reset_result_backend()          # fresh MemoryResultBackend
    reset_q_backend()               # clear queue singleton
    plugload._LOADED.clear()

    importlib.reload(nuvo_queue)    # make queue.py re‑resolve backend

    # stop any stray worker / dispatcher threads
    _shutdown_event.set()
    for t in list(threading.enumerate()):
        if t.name.startswith(("Worker-", "Dispatcher")):
            t.join(timeout=0.5)
    _shutdown_event.clear()

    plugreg._reset_for_tests()
    clear_queue()
    
    yield
    
    # ── TEAR‑DOWN ───────────────────────────────────────────────────────
    _shutdown_event.set()
    clear_queue()
    get_task_registry().clear()
    reset_result_backend()
    reset_q_backend()
    
    plugload._LOADED.clear()
    plugreg._reset_for_tests()
