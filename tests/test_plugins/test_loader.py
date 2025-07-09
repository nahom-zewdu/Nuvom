# tests/test_plugins/test_loader.py

"""
Unit‑tests for the hybrid plugin loader.

Covers:
    • TOML discovery (valid / invalid)
    • Entry‑point discovery
    • Legacy register() plugins
    • Duck‑typed Plugin classes
    • Version mismatch handling
"""

from types import SimpleNamespace, ModuleType

import textwrap

from nuvom.plugins import loader


# --------------------------------------------------------------------------- #
#  Utility helpers
# --------------------------------------------------------------------------- #
def _tmp_toml(tmp_path, content: str):
    file = tmp_path / ".nuvom_plugins.toml"
    file.write_text(textwrap.dedent(content), encoding="utf-8")
    return file


# --------------------------------------------------------------------------- #
#  TOML discovery
# --------------------------------------------------------------------------- #
def test_toml_targets_valid(tmp_path, monkeypatch):
    toml = _tmp_toml(
        tmp_path,
        """
        [plugins]
        modules = ["foo.bar", "baz.plugin:MyPlugin"]
        queue_backend  = ["my.queue:Q"]
        result_backend = ["my.result:R"]
        """,
    )
    monkeypatch.setattr(loader, "_TOML_PATH", toml)

    assert sorted(loader._toml_targets()) == sorted(
        ["foo.bar", "baz.plugin:MyPlugin", "my.queue:Q", "my.result:R"]
    )


def test_toml_targets_invalid(tmp_path, monkeypatch):
    toml = _tmp_toml(tmp_path, "not = [valid")
    monkeypatch.setattr(loader, "_TOML_PATH", toml)

    assert loader._toml_targets() == []


# --------------------------------------------------------------------------- #
#  Entry‑point discovery
# --------------------------------------------------------------------------- #
def test_entry_point_targets(monkeypatch):
    fake_ep = SimpleNamespace(value="mypkg.plugin:Plugin")
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda group=None: [fake_ep] if group == "nuvom" else [],
    )
    assert loader._entry_point_targets() == ["mypkg.plugin:Plugin"]


# --------------------------------------------------------------------------- #
#  Legacy register() loading
# --------------------------------------------------------------------------- #
def test_load_plugin_register_function(monkeypatch):
    called = {"flag": False}

    def dummy_register():
        called["flag"] = True

    # Force plugin discovery to only use this dummy spec
    monkeypatch.setattr(loader, "_iter_targets", lambda: ["dummy.module"])
    # Reset loader state
    loader._LOADED_SPECS.clear()

    # Simulate importlib returning a callable plugin
    monkeypatch.setattr("importlib.import_module", lambda _: dummy_register)

    loader.load_plugins()

    assert called["flag"], "Expected dummy_register() to be called"



# --------------------------------------------------------------------------- #
#  Duck‑typed Plugin class loading
# --------------------------------------------------------------------------- #
class GoodPlugin:
    api_version = "1.0"
    name = "good"
    provides = ["queue_backend"]
    requires = []

    def start(self, settings): ...
    def stop(self): ...


def test_load_plugin_class_success(monkeypatch):
    # Only return our test plugin spec
    monkeypatch.setattr(loader, "_iter_targets", lambda: ["plugin.good:GoodPlugin"])
    loader.LOADED_PLUGINS.clear()
    loader._LOADED_SPECS.clear()

    # Mock importlib to return a module with GoodPlugin
    fake_mod = ModuleType("plugin.good")
    fake_mod.GoodPlugin = GoodPlugin
    monkeypatch.setattr("importlib.import_module", lambda _: fake_mod)

    loader.load_plugins()

    # Check a plugin with name "good" is loaded
    assert any(p.name == "good" for p in loader.LOADED_PLUGINS), "Expected plugin 'good' to be loaded"



# --------------------------------------------------------------------------- #
#  Version mismatch → should skip
# --------------------------------------------------------------------------- #
class BadVersionPlugin:
    api_version = "99.99.0"
    name = "bad"
    provides = ["result_backend"]
    requires = []

    def start(self, settings): ...
    def stop(self): ...


def test_plugin_version_mismatch_skipped(monkeypatch):
    monkeypatch.setattr(loader, "_iter_targets", lambda: ["plugin.bad:Bad"])
    loader.LOADED_PLUGINS.clear()

    fake_mod = ModuleType("plugin.bad")
    fake_mod.Bad = BadVersionPlugin
    monkeypatch.setattr("importlib.import_module", lambda _: fake_mod)

    loader.load_plugins()
    assert "plugin.bad:Bad" not in loader.LOADED_PLUGINS
