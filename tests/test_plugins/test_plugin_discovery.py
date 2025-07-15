# tests/test_plugins/test_plugin_discovery.py

import textwrap
import pytest

import nuvom.plugins.loader as plugin_loader
from nuvom.plugins.registry import REGISTRY, _reset_for_tests


@pytest.fixture(autouse=True)
def reset_plugin_registry():
    """Reset plugin state and clear registry between tests."""
    _reset_for_tests()
    plugin_loader.LOADED_PLUGINS.clear()
    plugin_loader._LOADED_SPECS.clear()
    yield
    _reset_for_tests()


def test_builtin_plugins_are_registered():
    """Ensure that built-in queue/result backends are registered by default."""
    from nuvom.plugins import registry

    queue_cls = registry.get_queue_backend_cls("memory")
    result_cls = registry.get_result_backend_cls("file")

    assert queue_cls.__name__.endswith("JobQueue")
    assert result_cls.__name__.endswith("ResultBackend")


def test_plugin_duck_typing(monkeypatch, tmp_path):
    """Load plugin using a class that duck-types the Plugin protocol."""
    plugin_code = textwrap.dedent("""
        class DummyPlugin:
            api_version = "1.0"
            name = "dummy"
            provides = ["queue_backend"]

            def start(self, settings, **extras):
                self.started = True

            def stop(self):
                self.stopped = True
    """)

    mod_path = tmp_path / "myplugin.py"
    mod_path.write_text(plugin_code)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: ["myplugin:DummyPlugin"])
    monkeypatch.setattr(plugin_loader, "_toml_targets", lambda: [])

    plugin_loader.load_plugins()

    plugin = next(p for p in plugin_loader.LOADED_PLUGINS if p.name == "dummy")
    assert hasattr(plugin, "started")
    assert REGISTRY.get("queue_backend", "dummy") == plugin


def test_invalid_plugin_missing_fields(monkeypatch, tmp_path):
    """Plugins missing required fields should not be loaded or registered."""
    plugin_code = """
    class Incomplete:
        def start(self): pass
        def stop(self): pass
    """
    path = tmp_path / "bad.py"
    path.write_text(plugin_code)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: ["bad:Incomplete"])
    monkeypatch.setattr(plugin_loader, "_toml_targets", lambda: [])

    plugin_loader.load_plugins()

    assert not plugin_loader.LOADED_PLUGINS
    assert not REGISTRY.get("queue_backend", "incomplete")


def test_plugin_api_version_mismatch(monkeypatch, tmp_path):
    """Reject plugin with incompatible major api_version."""
    plugin_code = """
    class WrongVersion:
        api_version = "9.9"
        name = "old"
        provides = ["queue_backend"]

        def start(self, *a, **k): pass
        def stop(self): pass
    """
    path = tmp_path / "versioned.py"
    path.write_text(plugin_code)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: ["versioned:WrongVersion"])
    monkeypatch.setattr(plugin_loader, "_toml_targets", lambda: [])

    plugin_loader.load_plugins()

    assert "old" not in [p.name for p in plugin_loader.LOADED_PLUGINS]
    assert not REGISTRY.get("queue_backend", "old")


def test_duplicate_plugin_registration(monkeypatch, tmp_path):
    """Warn when duplicate plugin names are registered."""
    plugin_code = textwrap.dedent("""
        class Duplicate:
            api_version = "1.0"
            name = "conflict"
            provides = ["queue_backend"]

            def start(self, settings, **extras): pass
            def stop(self): pass
    """)

    path = tmp_path / "conflict.py"
    path.write_text(plugin_code)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: ["conflict:Duplicate", "conflict:Duplicate"])
    monkeypatch.setattr(plugin_loader, "_toml_targets", lambda: [])

    plugin_loader.load_plugins()

    assert [p.name for p in plugin_loader.LOADED_PLUGINS].count("conflict") == 1
    assert REGISTRY.get("queue_backend", "conflict") is not None


def test_legacy_register_callable(monkeypatch, tmp_path):
    plugin_code = textwrap.dedent("""\
        from nuvom.plugins.registry import REGISTRY
        def register():
            class Legacy:
                api_version = "1.0"
                name = "legacy"
                provides = ["queue_backend"]
                def start(self, s, **e): pass
                def stop(self): pass
            REGISTRY.register("queue_backend", "legacy", Legacy(), override=True)
    """)

    plugin_name = "legacyplugin_fix"
    mod_path = tmp_path / f"{plugin_name}.py"
    mod_path.write_text(plugin_code)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: [f"{plugin_name}:register"])
    monkeypatch.setattr(plugin_loader, "_toml_targets", lambda: [])

    import sys
    sys.modules.pop(plugin_name, None)

    plugin_loader.load_plugins()

    assert REGISTRY.get("queue_backend", "legacy") is not None



def test_load_from_toml(monkeypatch, tmp_path):
    """Load plugins defined via .nuvom_plugins.toml file."""
    plugin_code = textwrap.dedent("""
        class TomlPlugin:
            api_version = "1.0"
            name = "tomltest"
            provides = ["queue_backend"]
            def start(self, s, **e): pass
            def stop(self): pass
    """)

    mod = tmp_path / "mod_toml.py"
    mod.write_text(plugin_code)
    (tmp_path / ".nuvom_plugins.toml").write_text('[plugins]\nmodules = ["mod_toml:TomlPlugin"]')

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(plugin_loader, "_TOML_PATH", tmp_path / ".nuvom_plugins.toml")
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: [])

    plugin_loader.load_plugins()

    assert REGISTRY.get("queue_backend", "tomltest") is not None


def test_update_runtime_called(monkeypatch, tmp_path):
    """If a loaded plugin has update_runtime(), it should be called on re-load with extras."""
    plugin_code = textwrap.dedent("""
        class RuntimeCapable:
            api_version = "1.0"
            name = "runtime"
            provides = ["queue_backend"]

            def __init__(self):
                self.called = False

            def start(self, s, **e): pass
            def stop(self): pass
            def update_runtime(self, **kwargs): self.called = True
    """)

    mod_path = tmp_path / "runtime_plugin.py"
    mod_path.write_text(plugin_code)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: ["runtime_plugin:RuntimeCapable"])
    monkeypatch.setattr(plugin_loader, "_toml_targets", lambda: [])

    plugin_loader.load_plugins()
    plugin_loader.load_plugins(extras={"foo": "bar"})

    plugin = next(p for p in plugin_loader.LOADED_PLUGINS if p.name == "runtime")
    assert getattr(plugin, "called", False)


def test_plugin_import_failure(monkeypatch):
    """Fail gracefully if importing plugin module fails."""
    monkeypatch.setattr(plugin_loader, "_entry_point_targets", lambda: ["nonexistent:NothingHere"])
    monkeypatch.setattr(plugin_loader, "_toml_targets", lambda: [])

    plugin_loader.load_plugins()

    assert not plugin_loader.LOADED_PLUGINS
