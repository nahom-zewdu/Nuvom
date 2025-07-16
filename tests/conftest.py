# tests/conftest.py

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
    reset_result_backend()
    reset_q_backend()
    plugload.LOADED_PLUGINS.clear()
    plugload._LOADED_SPECS.clear()

    importlib.reload(nuvo_queue)

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
    
    plugload.LOADED_PLUGINS.clear()
    plugload._LOADED_SPECS.clear()

    plugreg._reset_for_tests()
