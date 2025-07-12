#  nuvom/plugins/contracts.py

"""
Plugin protocol & core version pinning.
"""

from __future__ import annotations
from abc import ABC, abstractmethod

API_VERSION = "1.0"

class Plugin(ABC):
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
    @abstractmethod
    def start(self, settings: dict, extras: dict | None = None) -> None:
        """
        Start plugin with config settings and optional runtime extras.

        Parameters
        ----------
        settings : dict
            Validated Nuvom configuration as dictionary.

        extras : dict, optional
            Runtime data passed by the core system (e.g. metrics provider).
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        ...
        
    def update_runtime(self, extras: dict) -> None:
        """
        Optional hook to receive runtime-only data like metrics providers.
        Default is no-op.
        """
        pass