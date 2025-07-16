# nuvom/plugins/registry.py

"""
Generic capability registry (queue_backend, result_backend, …).

Legacy helpers remain but emit a deprecation warning.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict
import warnings
import threading

# ──────────────────────────────────────────────────────────────
# Internal registry implementation
# ──────────────────────────────────────────────────────────────

class Registry:
    """Generic plugin registry mapping capabilities → {name: class} buckets."""

    def __init__(self) -> None:
        self._caps: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def register(self, cap: str, name: str, obj: Any, *, override: bool = False) -> None:
        name = name.lower()
        bucket = self._caps[cap]
        if name in bucket and not override:
            raise ValueError(f"{cap} provider '{name}' already registered")
        bucket[name] = obj

    def get(self, cap: str, name: str | None = None) -> Any | None:
        ensure_builtins_registered()
        bucket = self._caps.get(cap, {})

        if name:
            return bucket.get(name.lower())

        if len(bucket) == 1:
            return next(iter(bucket.values()))

        if not bucket:
            raise LookupError(f"No providers registered for capability: '{cap}'")

        raise LookupError(f"Multiple providers for '{cap}' registered. Specify one explicitly.")

REGISTRY = Registry()

# ──────────────────────────────────────────────────────────────
# Legacy shims — deprecated for removal in v1.0
# ──────────────────────────────────────────────────────────────

def _warn_legacy(fn: str) -> None:
    warnings.warn(
        f"{fn} is deprecated and will be removed in Nuvom 1.0. "
        "Use Plugin protocol-based registration instead.",
        DeprecationWarning,
        stacklevel=3,
    )

def register_queue_backend(name: str, cls: Any, *, override: bool = False) -> None:
    _warn_legacy("register_queue_backend()")
    REGISTRY.register("queue_backend", name, cls, override=override)

def register_result_backend(name: str, cls: Any, *, override: bool = False) -> None:
    _warn_legacy("register_result_backend()")
    REGISTRY.register("result_backend", name, cls, override=override)

def get_queue_backend_cls(name: str):
    return REGISTRY.get("queue_backend", name)

def get_result_backend_cls(name: str):
    return REGISTRY.get("result_backend", name)

# ──────────────────────────────────────────────────────────────
# Built-in provider registration
# ──────────────────────────────────────────────────────────────

_BUILTINS_REGISTERED = False
_REGISTERING_LOCK = threading.Lock()

def _register_builtins() -> None:
    from nuvom.queue_backends.memory_queue import MemoryJobQueue
    from nuvom.queue_backends.file_queue import FileJobQueue
    from nuvom.queue_backends.sqlite_queue import SQLiteJobQueue
    from nuvom.result_backends.memory_backend import MemoryResultBackend
    from nuvom.result_backends.file_backend import FileResultBackend
    from nuvom.result_backends.sqlite_backend import SQLiteResultBackend

    REGISTRY.register("queue_backend", "memory", MemoryJobQueue, override=True)
    REGISTRY.register("queue_backend", "file", FileJobQueue, override=True)
    REGISTRY.register("queue_backend", "sqlite", SQLiteJobQueue, override=True)

    REGISTRY.register("result_backend", "memory", MemoryResultBackend, override=True)
    REGISTRY.register("result_backend", "file", FileResultBackend, override=True)
    REGISTRY.register("result_backend", "sqlite", SQLiteResultBackend, override=True)

def ensure_builtins_registered() -> None:
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return
    with _REGISTERING_LOCK:
        if not _BUILTINS_REGISTERED:
            _register_builtins()
            _BUILTINS_REGISTERED = True

# ──────────────────────────────────────────────────────────────
# Test-only reset hook
# ──────────────────────────────────────────────────────────────

def _reset_for_tests():
    """
    Clear all registry buckets and reset built-in registration flag.
    For test isolation only.
    """
    global _BUILTINS_REGISTERED
    REGISTRY._caps.clear()
    _BUILTINS_REGISTERED = False
