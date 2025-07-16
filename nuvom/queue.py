# nuvom/queue.py

"""
Queue façade that delegates all persistence to a *pluggable* backend class.

Supports:
• Plugin-based resolution of queue backends
• Singleton lifecycle
• SQLite constructor injection (queue path)
"""

from __future__ import annotations

import threading
from typing import List, Optional

from nuvom.config import get_settings
from nuvom.job import Job
from nuvom.log import get_logger
from nuvom.plugins.loader import load_plugins
from nuvom.plugins.registry import get_queue_backend_cls

logger = get_logger()

_backend_singleton = None
_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# Backend factory
# --------------------------------------------------------------------------- #
def _resolve_backend():
    """
    Resolve and instantiate the concrete queue backend class.

    Resolution order:
    1. Load *all* plugins (entry-points and TOML)
    2. Lookup backend class from plugin registry
    3. If SQLite, inject path from config
    """
    settings = get_settings()
    load_plugins()  # ensure registry is populated

    backend_name = settings.queue_backend.strip().lower()
    backend_cls = get_queue_backend_cls(backend_name)

    if backend_cls is None:
        raise ValueError(
            f"[Queue] Unsupported queue backend: '{backend_name}'. "
            "Ensure it’s correctly registered or installed."
        )

    try:
        if backend_name == "sqlite":
            return backend_cls(settings.sqlite_queue_path or ".nuvom/queue.db")
        return backend_cls()  # default constructor
    except Exception as e:
        logger.exception("[Queue] Failed to instantiate backend: %s", backend_name)
        raise RuntimeError(f"Queue backend instantiation failed: {e}") from e


def get_queue_backend():
    """Return a *singleton* instance of the active queue backend."""
    global _backend_singleton
    if _backend_singleton is None:
        with _lock:
            if _backend_singleton is None:
                _backend_singleton = _resolve_backend()
    return _backend_singleton


def reset_backend() -> None:
    """
    **Testing-only helper** — reset cached backend instance.

    Next call to `get_queue_backend()` will resolve and create a fresh instance.
    """
    global _backend_singleton
    with _lock:
        _backend_singleton = None


# --------------------------------------------------------------------------- #
# Queue API (Forward to backend)
# --------------------------------------------------------------------------- #
def enqueue(job: Job) -> None:
    """Add *job* to the configured backend."""
    get_queue_backend().enqueue(job)


def dequeue(timeout: int = 1) -> Optional[Job]:
    """Blocking pop of a single job (`None` if timed-out)."""
    if timeout < 0:
        raise ValueError("timeout must be non-negative")
    return get_queue_backend().dequeue(timeout)


def pop_batch(batch_size: int = 1, timeout: int = 1) -> List[Job]:
    """Return up to *batch_size* jobs (may be fewer if queue is shorter)."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if timeout < 0:
        raise ValueError("timeout must be non-negative")
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
        Number of jobs removed (implementation-specific).
    """
    return get_queue_backend().clear()
