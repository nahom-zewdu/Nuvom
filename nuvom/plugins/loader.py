# nuvom/plugins/loader.py

"""
Hybrid plugin loader (back-compatible with v0.8).

Discovery order
---------------
1. Python entry-points in the ``nuvom`` group
2. ``.nuvom_plugins.toml`` (legacy)

Accepted plugin shapes
----------------------
• Class that implements / duck-types the Plugin protocol
• Legacy callable ``register()`` (DEPRECATED - emits warning)
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import tomllib
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Set
import threading

from nuvom.log import get_logger
from nuvom.plugins.contracts import API_VERSION, Plugin
from nuvom.plugins.registry import REGISTRY

# --------------------------------------------------------------------------- #
# Globals
# --------------------------------------------------------------------------- #
_TOML_PATH = Path(".nuvom_plugins.toml")

_LOADED_SPECS: Set[str] = set()        # memoised "module[:attr]"
LOADED_PLUGINS: Set[Plugin] = set()    # instantiated plugin objects

logger = get_logger()
_load_lock = threading.Lock()          # thread-safe guard around first load

# --------------------------------------------------------------------------- #
# Discovery helpers
# --------------------------------------------------------------------------- #
def _toml_targets() -> list[str]:
    if not _TOML_PATH.exists():
        return []

    try:
        data = tomllib.loads(_TOML_PATH.read_text("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        logger.error("[Plugins] Invalid TOML in %s – %s", _TOML_PATH, exc)
        return []

    plugin_block = data.get("plugins", {})
    targets: list[str] = []
    targets.extend(plugin_block.get("modules", []))  # legacy key

    for key, value in plugin_block.items():
        if key != "modules" and isinstance(value, list):
            targets.extend(value)

    return targets


def _entry_point_targets() -> list[str]:
    """Return ``pkg.mod:Class`` specs from the *nuvom* entry‑point group."""
    try:
        return [ep.value for ep in md.entry_points(group="nuvom")]
    except TypeError:  # older importlib.metadata (<3.10)
        return [ep.value for ep in md.entry_points().get("nuvom", [])]


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
    mod_path, _, attr = spec.partition(":")
    module: ModuleType = importlib.import_module(mod_path)
    return getattr(module, attr) if attr else module


def _is_duck_plugin(cls: type) -> bool:
    required = ("api_version", "name", "provides", "start", "stop")
    return all(hasattr(cls, attr) for attr in required)


def _major_mismatch(core: str, plugin: str) -> bool:
    return core.split(".", 1)[0] != plugin.split(".", 1)[0]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def load_plugins(settings: dict | None = None) -> None:
    """
    Import, instantiate, and start all plugins exactly once per process.

    Args:
        settings: Optional dict mapping plugin.name → config passed to Plugin.start()
    """
    if _LOADED_SPECS:
        return

    cfg = settings or {}

    with _load_lock:
        if _LOADED_SPECS:  # double‑checked after acquiring lock
            return

        for spec in _iter_targets():
            if spec in _LOADED_SPECS:
                continue

            try:
                target = _import_target(spec)

                # ─── Legacy callable path ────────────────────────────────────
                if callable(target) and not isinstance(target, type):
                    warnings.warn(
                        "Legacy plugin register() style is deprecated and will be "
                        "removed in Nuvom 1.0. Implement the Plugin protocol.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    target()  # run register()
                    logger.info("[Plugin‑Legacy] %s loaded", spec)
                    _LOADED_SPECS.add(spec)
                    continue

                # ─── Class path ─────────────────────────────────────────────
                if isinstance(target, type):
                    try:
                        subclass_ok = issubclass(target, Plugin)
                    except TypeError:
                        subclass_ok = False

                    if not (subclass_ok or _is_duck_plugin(target)):
                        logger.warning("[Plugin] %s does not implement Plugin protocol", spec)
                        continue

                    plugin_cls = target

                    # API version gate
                    if _major_mismatch(API_VERSION, plugin_cls.api_version):
                        logger.error(
                            "[Plugin] %s api_version %s incompatible with core %s",
                            plugin_cls.__name__,
                            plugin_cls.api_version,
                            API_VERSION,
                        )
                        continue

                    plugin: Plugin = plugin_cls()  # type: ignore[assignment]
                    plugin_cfg = cfg.get(plugin.name, {})
                    plugin.start(plugin_cfg)
                    LOADED_PLUGINS.add(plugin)

                    # Register each capability this plugin claims to provide
                    for cap in plugin.provides:
                        try:
                            REGISTRY.register(cap, plugin.name, plugin, override=True)
                        except ValueError as e:
                            logger.warning("[Plugin] %s registration conflict: %s", plugin.name, e)

                    logger.info("[Plugin] %s (%s) loaded", plugin.name, plugin_cls.__name__)
                    _LOADED_SPECS.add(spec)
                    continue

                logger.warning("[Plugin] %s does not expose a Plugin subclass or legacy register()", spec)

            except Exception as exc:  # broad capture for logging
                logger.exception("[Plugin] Failed to load %s – %s", spec, exc)

        # Memoise any built‑in Plugin instances (rare but allowed)
        for cap in ("queue_backend", "result_backend"):
            for name, obj in REGISTRY._caps.get(cap, {}).items():
                if isinstance(obj, Plugin):
                    _LOADED_SPECS.add(name)


def shutdown_plugins() -> None:
    """Invoke .stop() on all loaded plugins."""
    for plugin in list(LOADED_PLUGINS):
        stop_fn = getattr(plugin, "stop", None)
        if callable(stop_fn):
            try:
                logger.info("[Plugin] Stopping %s (%s)…", plugin.name, plugin.__class__.__name__)
                stop_fn()
            except Exception as e:
                logger.warning("[Plugin] %s.stop() failed – %s", plugin.name, e)
