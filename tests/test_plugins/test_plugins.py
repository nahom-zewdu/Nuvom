# tests/test_plugins.py

"""
Tests for Nuvom’s plugin system (registry + loader).

These tests spin up fake modules on sys.modules so we don’t need real files.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from pathlib import Path
import tomllib
import textwrap

import pytest

from nuvom.plugins import registry as plugreg
from nuvom.plugins import loader as plugload


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _fake_module(modname: str, calls: list[str], as_queue: bool = False) -> None:
    """
    Patch sys.modules with a fake plugin module.

    If `as_queue` is True, will register a dummy queue backend using legacy register().
    """
    import types
    import sys
    from nuvom.plugins.registry import REGISTRY

    mod = types.ModuleType(modname)

    def register():
        calls.append("register-called")
        if as_queue:
            REGISTRY.register("queue_backend", "fake", object, override=True)

    mod.register = register
    sys.modules[modname] = mod



# --------------------------------------------------------------------------- #
#  Tests
# --------------------------------------------------------------------------- #
def test_registry_basic_registration():
    class MemBackend: ...
    plugreg.register_result_backend("mydb", MemBackend, override=True)
    assert plugreg.get_result_backend_cls("mydb") is MemBackend

    # Duplicate without override should raise
    with pytest.raises(ValueError):
        plugreg.register_result_backend("mydb", MemBackend)

def test_loader_imports_and_register(tmp_path: Path, monkeypatch):
    calls: list[str] = []
    _fake_module("myplugin.mod", calls, as_queue=True)

    cfg = tmp_path / ".nuvom_plugins.toml"
    cfg.write_text(
        textwrap.dedent(
            """
            [plugins]
            modules = ["myplugin.mod:register"]
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(plugload, "_TOML_PATH", cfg)
    plugload._LOADED.clear()  # Important: reset for test isolation
    plugload.load_plugins()

    assert "myplugin.mod:register" in plugload._LOADED
    assert "register-called" in calls


def test_queue_resolution_with_plugin(monkeypatch):
    """
    queue.get_queue_backend() should be able to resolve a queue backend
    registered by a plugin.
    """
    from nuvom import queue as nuv_queue
    from nuvom.config import override_settings

    class InMem:  # minimal “backend”
        def enqueue(self, *_): ...
        def dequeue(self, *_): return None
        def pop_batch(self, *_): return []
        def qsize(self): return 0
        def clear(self): return 0

    plugreg.register_queue_backend("plugmem", InMem, override=True)
    override_settings(queue_backend="plugmem")

    # Fresh import to force function to re‑resolve backend
    import importlib
    importlib.reload(nuv_queue)

    backend = nuv_queue.get_queue_backend()
    assert isinstance(backend, InMem)
