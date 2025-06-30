#  nuvom/plugins/contracts.py

"""
Plugin protocol & core version pinning.
"""

from __future__ import annotations
from typing import Protocol, runtime_checkable, Any

API_VERSION = "1.0"


@runtime_checkable
class Plugin(Protocol):
    """
    Formal contract every third‑party plugin must implement.

    Attributes
    ----------
    api_version : str
        Must share major version with ``nuvom.plugins.API_VERSION``.
    name : str
        Unique identifier (e.g. "sqlite", "redis").
    provides : list[str]
        Capabilities this plugin offers (e.g. ["queue_backend"]).
    requires : list[str]
        Optional capabilities this plugin depends on.
    """

    api_version: str
    name: str
    provides: list[str]
    requires: list[str]

    # Minimal lifecycle hooks
    def start(self, settings: dict[str, Any]) -> None: ...
    def stop(self) -> None: ...
