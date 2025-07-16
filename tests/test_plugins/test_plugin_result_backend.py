# tests/test_plugins/test_plugin_result_backend.py

import os
import sys
import textwrap
from pathlib import Path

from nuvom import result_store
from nuvom.config import get_settings
from nuvom.result_store import reset_backend
from nuvom.plugins import loader


def test_plugin_result_backend(monkeypatch, tmp_path):
    """
    End‑to‑end check: a result backend registered by a *plugin* is selected
    when `NUVOM_RESULT_BACKEND` points to it.
    """
    # ────────────────────────────────────────────────────────────────────
    # 1. Write a one‑file plugin with a DummyResultBackend
    # ────────────────────────────────────────────────────────────────────
    plugin_source = textwrap.dedent(
        """
        from nuvom.plugins.contracts import Plugin

        class DummyResultBackend:
            def set_result(self, *_, **__): pass
            def get_result(self, job_id):      return {"dummy": True, "job_id": job_id}
            def set_error (self, *_, **__): pass
            def get_error(self, job_id):      return {"error": "Dummy", "job_id": job_id}

        class HelloPlugin(Plugin):
            api_version = "1.0"
            name        = "hello_plugin"
            provides    = ["result_backend"]

            def start(self, _settings):
                from nuvom.plugins.registry import register_result_backend
                register_result_backend("dummy", DummyResultBackend, override=True)

            def stop(self): pass
        """
    )
    plugin_file = tmp_path / "hello_plugin.py"
    plugin_file.write_text(plugin_source, encoding="utf‑8")

    sys.path.insert(0, str(tmp_path))  # allow `import hello_plugin`

    # ────────────────────────────────────────────────────────────────────
    # 2. Write test-local .nuvom_plugins.toml
    # ────────────────────────────────────────────────────────────────────
    toml_path = tmp_path / ".nuvom_plugins.toml"
    toml_path.write_text(
        '[plugins]\nresult_backend = ["hello_plugin:HelloPlugin"]\n', encoding="utf‑8"
    )

    # ────────────────────────────────────────────────────────────────────
    # 3. Patch global TOML_PATH *before* any plugin loading
    # ────────────────────────────────────────────────────────────────────
    monkeypatch.setattr(loader, "_TOML_PATH", toml_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NUVOM_RESULT_BACKEND", "dummy")

    # Force new settings and plugin state
    get_settings(force_reload=True)
    reset_backend()
    loader._LOADED_SPECS.clear()
    loader.LOADED_PLUGINS.clear()

    # ────────────────────────────────────────────────────────────────────
    # 4. Access the backend — should trigger plugin load from TOML
    # ────────────────────────────────────────────────────────────────────
    result_store.set_result("abc", "func", result=123)
    res = result_store.get_result("abc")

    assert res["dummy"] is True
    assert res["job_id"] == "abc"
