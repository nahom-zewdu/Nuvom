# nuvom/result_backends/base.py

"""
Abstract interface for result backends that persist job outcomes.

All concrete backends (memory, file, SQLite, plugin-provided) **must**
implement this contract.

Changes
-------
* Added `@abstractmethod` decorator to `list_jobs`
* Added `pass` body to satisfy Python's syntax
* Fixed docstring typos and clarified return types
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseResultBackend(ABC):
    """
    Interface for persisting job results and errors.

    Methods
    -------
    set_result(...)  : Store successful job outcome with metadata
    get_result(...)  : Fetch stored result
    set_error(...)   : Store failure metadata
    get_error(...)   : Fetch stored error / traceback
    get_full(...)    : Fetch full metadata for a job
    list_jobs(...)   : Enumerate all stored jobs (optional extension)
    """

    # ------------------------------------------------------------------ #
    # Success path
    # ------------------------------------------------------------------ #
    @abstractmethod
    def set_result(
        self,
        job_id: str,
        func_name: str,
        result: Any,
        *,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ) -> None:
        """Persist result along with job metadata."""
        ...

    @abstractmethod
    def get_result(self, job_id: str) -> Any:
        """Return stored result object or ``None``."""
        ...

    # ------------------------------------------------------------------ #
    # Failure path
    # ------------------------------------------------------------------ #
    @abstractmethod
    def set_error(
        self,
        job_id: str,
        func_name: str,
        error: Exception,
        *,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        retries_left: Optional[int] = None,
        attempts: Optional[int] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None,
    ) -> None:
        """Persist exception info and metadata."""
        ...

    @abstractmethod
    def get_error(self, job_id: str) -> Optional[str]:
        """Return stored error/traceback string or ``None``."""
        ...

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    @abstractmethod
    def get_full(self, job_id: str) -> Optional[Dict]:
        """Return full metadata dict for given job ID."""
        ...

    @abstractmethod
    def list_jobs(self) -> List[Dict]:
        """Return a list of all stored job records."""
        ...
