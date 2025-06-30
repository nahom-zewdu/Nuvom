# nuvom/plugins/registry.py

"""
Generic capability registry (queue_backend, result_backend, …).

Legacy helpers remain but emit a deprecation warning.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict

import warnings


class _Registry:
    """Internal generic registry backed by a bucket‑dict."""

    def __init__(self) -> None:
        self._caps: Dict[str, Dict[str, Any]] = defaultdict(dict)

    # ----------------------------------------------------- #
    # Public generic API
    # ----------------------------------------------------- #
    def register(self, cap: str, name: str, obj: Any, *, override: bool = False) -> None:
        bucket = self._caps[cap]
        if name in bucket and not override:
            raise ValueError(f"{cap} provider '{name}' already registered")
        bucket[name] = obj

    def get(self, cap: str, name: str | None = None) -> Any | None:
        ensure_builtins_registered()  
        bucket = self._caps.get(cap, {})
        if name is not None:
            return bucket.get(name)
        # If only one implementation exists, return it implicitly
        if len(bucket) == 1:
            return next(iter(bucket.values()))
        
        raise LookupError(f"Multiple {cap} providers; specify one.")


REGISTRY = _Registry()

# --------------------------------------------------------- #
# Back‑compat shims (will be removed in v1.0)
# --------------------------------------------------------- #
def _warn_legacy(fn: str) -> None:
    warnings.warn(
        f"{fn} is deprecated and will be removed in Nuvom 1.0. "
        "Implement the Plugin protocol instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def register_queue_backend(name: str, cls: Any, *, override: bool = False) -> None:
    _warn_legacy("register_queue_backend()")
    REGISTRY.register("queue_backend", name.lower(), cls, override=override)


def register_result_backend(name: str, cls: Any, *, override: bool = False) -> None:
    _warn_legacy("register_result_backend()")
    REGISTRY.register("result_backend", name.lower(), cls, override=override)


def get_queue_backend_cls(name: str):
    return REGISTRY.get("queue_backend", name.lower())


def get_result_backend_cls(name: str):
    return REGISTRY.get("result_backend", name.lower())


# --------------------------------------------------------- #
# Built‑ins (memory / file / sqlite) registered here
# --------------------------------------------------------- #
def _register_builtins() -> None:
    from nuvom.queue_backends.memory_queue import MemoryJobQueue
    from nuvom.queue_backends.file_queue import FileJobQueue
    from nuvom.result_backends.memory_backend import MemoryResultBackend
    from nuvom.result_backends.file_backend import FileResultBackend
    from nuvom.result_backends.sqlite_backend import SQLiteResultBackend

    REGISTRY.register("queue_backend", "memory", MemoryJobQueue, override=True)
    REGISTRY.register("queue_backend", "file", FileJobQueue, override=True)

    REGISTRY.register("result_backend", "memory", MemoryResultBackend, override=True)
    REGISTRY.register("result_backend", "file", FileResultBackend, override=True)
    REGISTRY.register("result_backend", "sqlite", SQLiteResultBackend, override=True)


_BUILTINS_REGISTERED = False
_REGISTERING = False

def ensure_builtins_registered() -> None:
    global _BUILTINS_REGISTERED, _REGISTERING
    if _BUILTINS_REGISTERED or _REGISTERING:
        return
    _REGISTERING = True
    try:
        _register_builtins()
        _BUILTINS_REGISTERED = True
    finally:
        _REGISTERING = False
