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
def _fake_module(name: str, register_calls: list[str], *, as_queue=False):
    """
    Create an in‑memory module with optional `register()` callable.
    If `as_queue=True`, the register() will add a dummy queue backend.
    """
    mod = ModuleType(name)
    if as_queue:

        class DummyQueue:
            def enqueue(self, *_): ...
            def dequeue(self, *_): ...
            def pop_batch(self, *_): return []
            def qsize(self): return 0
            def clear(self): return 0

        def _reg():
            plugreg.register_queue_backend("dummy", DummyQueue, override=True)
            register_calls.append("called")

        mod.register = _reg  # type: ignore[attr-defined]

    sys.modules[name] = mod
    return mod


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
    """
    • Write a .nuvom_plugins.toml pointing to a fake module
    • Ensure loader imports it and the module’s register() runs
    """
    calls: list[str] = []
    _fake_module("myplugin.mod", calls, as_queue=True)

    cfg = tmp_path / ".nuvom_plugins.toml"
    cfg.write_text(
        textwrap.dedent(
            """
            [plugins]
            modules = ["myplugin.mod"]
            """
        ),
        encoding="utf-8",
    )

    # Monkey‑patch loader to look at tmp_path
    monkeypatch.setattr(plugload, "_CONFIG_PATH", cfg)

    plugload.load_plugins()
    assert "myplugin.mod" in plugload._PLUGINS_LOADED
    assert calls == ["called"]  # register() executed
    assert plugreg.get_queue_backend_cls("dummy") is not None


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
