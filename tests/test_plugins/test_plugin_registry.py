# tests/plugins/test_registry.py
"""
Unit‑tests for the generic plugin `Registry` (nuvom.plugins.registry).

The test‑suite focuses on:

1. Basic registration / retrieval round‑trip
2. Duplicate protection vs. `override=True`
3. Resolution semantics when name is omitted
4. Built‑in back‑compat shims (`register_queue_backend`, etc.)
"""

from types import SimpleNamespace
import pytest

from nuvom.plugins.registry import (
    REGISTRY,
    Registry,
    register_queue_backend,
    register_result_backend,
)


# --------------------------------------------------------------------------- #
#  Helpers / fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch):
    """
    Patch the global `REGISTRY` with a brand‑new instance for each test so that
    state from other tests (or the real runtime) cannot bleed in.
    """
    fresh = Registry()
    monkeypatch.setattr("nuvom.plugins.registry.REGISTRY", fresh, raising=True)
    yield fresh  # provide the patched instance to the test


def _dummy(name):
    """Return a unique dummy class for registration."""
    return type(name, (), {})


# --------------------------------------------------------------------------- #
#  Test‑cases
# --------------------------------------------------------------------------- #
def test_basic_register_and_get(_fresh_registry: Registry):
    cls = _dummy("MyQ")
    _fresh_registry.register("queue_backend", "myq", cls)

    resolved = _fresh_registry.get("queue_backend", "myq")
    assert resolved is cls


def test_duplicate_registration_raises(_fresh_registry: Registry):
    cls1 = _dummy("One")
    cls2 = _dummy("Two")

    _fresh_registry.register("queue_backend", "dup", cls1)
    with pytest.raises(ValueError):
        _fresh_registry.register("queue_backend", "dup", cls2)


def test_override_replaces_previous(_fresh_registry: Registry):
    cls1 = _dummy("Old")
    cls2 = _dummy("New")

    _fresh_registry.register("result_backend", "swap", cls1)
    _fresh_registry.register("result_backend", "swap", cls2, override=True)

    assert _fresh_registry.get("result_backend", "swap") is cls2


def test_get_without_name_single_provider(_fresh_registry: Registry):
    cls = _dummy("Solo")
    _fresh_registry.register("queue_backend", "solo", cls)

    # Name omitted: should succeed because only one provider exists
    assert _fresh_registry.get("queue_backend") is cls


def test_get_without_name_multiple_providers_raises(_fresh_registry: Registry):
    _fresh_registry.register("queue_backend", "a", _dummy("A"))
    _fresh_registry.register("queue_backend", "b", _dummy("B"))

    with pytest.raises(LookupError):
        _fresh_registry.get("queue_backend")


# --------------------------------------------------------------------------- #
#  Legacy shim smoke‑test
# --------------------------------------------------------------------------- #
def test_legacy_shims_register_backend(_fresh_registry: Registry):
    q_cls = _dummy("LegacyQ")
    r_cls = _dummy("LegacyR")

    register_queue_backend("legacyq", q_cls, override=True)
    register_result_backend("legacyr", r_cls, override=True)

    assert _fresh_registry.get("queue_backend", "legacyq") is q_cls
    assert _fresh_registry.get("result_backend", "legacyr") is r_cls
