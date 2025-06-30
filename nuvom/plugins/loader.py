# nuvom/plugins/loader.py

"""
nuvom/plugins/loader.py
=======================

Hybrid plugin loader (back‑compatible with v0.8).

• Discovers plugins from **Python entry‑points** *and* the legacy
  `.nuvom_plugins.toml` file.
• Accepts either a class implementing the `Plugin` protocol **or**
  a legacy callable `register()` function (deprecation‑warned).
• Guards against double‑loading by memoising every spec in `_LOADED`.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import tomllib
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Set

from nuvom.log import logger
from nuvom.plugins.contracts import API_VERSION, Plugin           # new protocol
from nuvom.plugins.registry import REGISTRY                       # generic registry

# --------------------------------------------------------------------------- #
# Globals
# --------------------------------------------------------------------------- #
_TOML_PATH = Path(".nuvom_plugins.toml")
_LOADED: Set[str] = set()            # memoised "module[:attr]" specs


# --------------------------------------------------------------------------- #
# Discovery helpers
# --------------------------------------------------------------------------- #
def _toml_targets() -> list[str]:
    """Read legacy TOML file and return the list of module specs."""
    if not _TOML_PATH.exists():
        return []
    try:
        data = tomllib.loads(_TOML_PATH.read_text("utf-8"))
        return list(data.get("plugins", {}).get("modules", []))
    except tomllib.TOMLDecodeError as exc:
        logger.error("[Plugins] Invalid TOML in %s – %s", _TOML_PATH, exc)
        return []


def _entry_point_targets() -> list[str]:
    """Return `pkg.mod:Class` specs from the *nuvom* entry‑point group."""
    return [ep.value for ep in md.entry_points(group="nuvom")]


def _iter_targets():
    """Yield every unique discovery spec (entry‑points first, then TOML)."""
    seen: set[str] = set()
    for spec in _entry_point_targets() + _toml_targets():
        if spec not in seen:
            seen.add(spec)
            yield spec


# --------------------------------------------------------------------------- #
# Import helpers
# --------------------------------------------------------------------------- #
def _import_target(spec: str) -> Any:
    """
    Import `"package.module:attr"` or bare `"package.module"`.

    Returns the attribute (callable/class) **or** the module object.
    """
    mod_path, _, attr = spec.partition(":")
    module: ModuleType = importlib.import_module(mod_path)
    return getattr(module, attr) if attr else module


def _major_mismatch(core: str, plugin: str) -> bool:
    return core.split(".", 1)[0] != plugin.split(".", 1)[0]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def load_plugins(settings: dict | None = None) -> None:
    """
    Import & register all plugins exactly once per process.

    Parameters
    ----------
    settings :
        Optional dict of per‑plugin configuration (passed to `plugin.start()`).
    """
    if _LOADED:
        return

    cfg = settings or {}

    for spec in _iter_targets():
        if spec in _LOADED:
            continue

        try:
            target = _import_target(spec)

            # ── Legacy path: callable `register()` ----------------------
            if callable(target) and not isinstance(target, type):
                warnings.warn(
                    "Legacy plugin register() style is deprecated and will "
                    "be removed in Nuvom 1.0. Implement the Plugin protocol.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                target()
                logger.info("[Plugin‑Legacy] %s loaded", spec)
                _LOADED.add(spec)
                continue

            # ── New path: class implementing `Plugin` -------------------
            if isinstance(target, type) and issubclass(target, Plugin):
                if _major_mismatch(API_VERSION, target.api_version):
                    logger.error(
                        "[Plugin] %s api_version %s incompatible with core %s",
                        target.__name__, target.api_version, API_VERSION,
                    )
                    continue

                plugin: Plugin = target()
                plugin.start(cfg.get(plugin.name, {}))

                # Register first advertised capability; plugin can register more itself
                REGISTRY.register(plugin.provides[0], plugin.name, plugin, override=True)
                logger.info("[Plugin] %s (%s) loaded", plugin.name, plugin.__class__.__name__)

                _LOADED.add(spec)
                continue

            # ── Unknown artefact ----------------------------------------
            logger.warning("[Plugin] %s does not expose a Plugin or register()", spec)

        except Exception as exc:
            logger.exception("[Plugin] Failed to load %s – %s", spec, exc)
            
    for cap in ("queue_backend", "result_backend"):
        for name, obj in REGISTRY._caps.get(cap, {}).items():
            if isinstance(obj, Plugin) and obj.name not in _LOADED:
                _LOADED.add(obj.name)