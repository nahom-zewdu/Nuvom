# nuvom/queue.py

"""
nuvom/queue.py
==============

Queue façade that delegates all persistence to a *pluggable* backend class.

Key improvements in this revision
---------------------------------
1. **Automatic plugin discovery** – calls ``plugins.loader.load_plugins()`` the
   first time a backend is requested, so “pip‑installed” queue providers are
   picked up without any manual bootstrap code.

2. **Reset helper for tests** – `reset_backend()` clears the singleton so
   functional tests can swap implementations via ``override_settings()``.
"""

from __future__ import annotations

from typing import List, Optional

from nuvom.config import get_settings
from nuvom.job import Job
from nuvom.plugins.loader import load_plugins
from nuvom.plugins.registry import get_queue_backend_cls

# ─────────────────────────────────────────────────────────────────────────────
# Module‑level cache (one backend instance per process)
# ─────────────────────────────────────────────────────────────────────────────
_backend_singleton = None


def _resolve_backend():
    """
    Resolve & instantiate the concrete queue backend class.

    Resolution order
    ----------------
    1. Load *all* plugins (entry‑points **and** legacy TOML) exactly once.
    2. Look up the short name from ``NUVOM_QUEUE_BACKEND`` in the plugin
       registry.
    3. Instantiate it (no‑arg ctor).  Raises ``ValueError`` if not found.
    """
    load_plugins()                                              # ensure registry is populated

    backend_name = get_settings().queue_backend.lower()
    backend_cls = get_queue_backend_cls(backend_name)

    if backend_cls is None:                                     # defensive – mis‑configuration
        raise ValueError(f"Unsupported or unregistered queue backend: {backend_name!r}")

    return backend_cls()


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_queue_backend():
    """Return a *singleton* instance of the active queue backend."""
    global _backend_singleton
    if _backend_singleton is None:
        _backend_singleton = _resolve_backend()
    return _backend_singleton


def reset_backend() -> None:
    """
    **Testing‑only helper** – clear the cached instance so the next call to
    :pyfunc:`get_queue_backend()` re‑creates it.  Useful when a test changes
    ``override_settings(queue_backend="…")`` on the fly.
    """
    global _backend_singleton
    _backend_singleton = None


# ─────────────────────────────────────────────────────────────────────────────
# Thin convenience wrappers – keep core code readable
# ─────────────────────────────────────────────────────────────────────────────
def enqueue(job: Job) -> None:
    """Add *job* to the configured backend."""
    get_queue_backend().enqueue(job)


def dequeue(timeout: int = 1) -> Optional[Job]:
    """Blocking pop of a single job (``None`` if timed‑out)."""
    return get_queue_backend().dequeue(timeout)


def pop_batch(batch_size: int = 1, timeout: int = 1) -> List[Job]:
    """Return up to *batch_size* jobs (may be fewer if queue shorter)."""
    return get_queue_backend().pop_batch(batch_size=batch_size, timeout=timeout)


def qsize() -> int:
    """Current length of the queue."""
    return get_queue_backend().qsize()


def clear() -> int:
    """
    Remove **all** jobs from the queue backend.

    Returns
    -------
    int
        Number of jobs removed (implementation‑specific).
    """
    return get_queue_backend().clear()
