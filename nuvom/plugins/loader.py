# nuvom/plugins/loader.py

"""
Hybrid plugin loader (back-compatible with v0.8).

Discovery order:
---------------
1. Python entry-points in the ``nuvom`` group
2. ``.nuvom_plugins.toml`` (legacy format)

Accepted plugin shapes:
-----------------------
• Class that implements / duck-types the Plugin protocol
• Legacy callable ``register()`` (DEPRECATED – emits warning)
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

# Set of "module[:attr]" spec strings that have been successfully loaded
_LOADED_SPECS: Set[str] = set()

# Set of instantiated Plugin objects that are active in the current process
LOADED_PLUGINS: Set[Plugin] = set()

logger = get_logger()
_load_lock = threading.Lock()  # Protects against concurrent plugin load attempts

# --------------------------------------------------------------------------- #
# Discovery helpers
# --------------------------------------------------------------------------- #

def _toml_targets() -> list[str]:
    """Extract plugin specs from the legacy TOML file."""
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
        if key != "modules":
            if isinstance(value, list):
                targets.extend(value)
            elif isinstance(value, str):
                targets.append(value)

    return targets


def _entry_point_targets() -> list[str]:
    """Return ``pkg.mod:Class`` specs from the *nuvom* entry-point group."""
    try:
        return [ep.value for ep in md.entry_points(group="nuvom")]
    except TypeError:  # fallback for Python <3.10
        return [ep.value for ep in md.entry_points().get("nuvom", [])]


def _iter_targets():
    """Yield every unique discovery spec in correct order (entry-points then TOML)."""
    seen: set[str] = set()
    for spec in _entry_point_targets() + _toml_targets():
        if spec not in seen:
            seen.add(spec)
            yield spec

# --------------------------------------------------------------------------- #
# Import helpers
# --------------------------------------------------------------------------- #

def _import_target(spec: str) -> Any:
    """Dynamically import a plugin from a 'module[:attr]' spec string."""
    mod_path, _, attr = spec.partition(":")
    module: ModuleType = importlib.import_module(mod_path)
    return getattr(module, attr) if attr else module


def _is_duck_plugin(cls: type) -> bool:
    """Check whether a class conforms to the expected Plugin protocol shape."""
    required = ("api_version", "name", "provides", "start", "stop")
    return all(hasattr(cls, attr) for attr in required)


def _major_mismatch(core: str, plugin: str) -> bool:
    """True if core and plugin API versions differ in major version."""
    return core.split(".", 1)[0] != plugin.split(".", 1)[0]

# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def load_plugins(settings: dict | None = None, extras: dict | None = None) -> None:
    """
    Discover, import, and start all plugins exactly once per process.

    Args:
        settings: Optional dict mapping plugin.name → config dict passed to Plugin.start()
        extras: Optional runtime-only values injected into plugin start() or update_runtime()
    """
    cfg = settings or {}
    rt = extras or {}

    with _load_lock:
        if _LOADED_SPECS:
            # Already initialized – patch plugins that support update_runtime()
            for plugin in LOADED_PLUGINS:
                if hasattr(plugin, "update_runtime"):
                    try:
                        plugin.update_runtime(**rt)
                    except Exception as e:
                        logger.warning("[Plugin] %s.update_runtime() failed – %s", plugin.name, e)
            return

        for spec in _iter_targets():
            if spec in _LOADED_SPECS:
                continue

            try:
                target = _import_target(spec)

                # ─── Legacy callable plugins ─────────────────────────────────
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

                # ─── Plugin class style ─────────────────────────────────────
                if isinstance(target, type):
                    try:
                        subclass_ok = issubclass(target, Plugin)
                    except TypeError:
                        subclass_ok = False

                    if not (subclass_ok or _is_duck_plugin(target)):
                        logger.warning("[Plugin] %s does not implement Plugin protocol", spec)
                        continue

                    plugin_cls = target

                    # Version compatibility check
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

                    # Start plugin with config + runtime extras
                    plugin.start(plugin_cfg, **rt)
                    LOADED_PLUGINS.add(plugin)

                    # Register each capability this plugin provides
                    for cap in plugin.provides:
                        try:
                            REGISTRY.register(cap, plugin.name, plugin, override=True)
                        except ValueError as e:
                            logger.warning("[Plugin] %s registration conflict: %s", plugin.name, e)

                    logger.info("[Plugin] %s (%s) loaded", plugin.name, plugin_cls.__name__)
                    _LOADED_SPECS.add(spec)
                    continue

                logger.warning("[Plugin] %s does not expose a Plugin subclass or legacy register()", spec)

            except Exception as exc:
                logger.exception("[Plugin] Failed to load %s – %s", spec, exc)

        # ─── Memoize built-in Plugin instances (if preloaded manually) ─────
        for cap in ("queue_backend", "result_backend"):
            for name, obj in REGISTRY._caps.get(cap, {}).items():
                if isinstance(obj, Plugin):
                    _LOADED_SPECS.add(name)


def shutdown_plugins() -> None:
    """
    Gracefully shut down all loaded plugins by calling their .stop() method.
    """
    for plugin in list(LOADED_PLUGINS):
        stop_fn = getattr(plugin, "stop", None)
        if callable(stop_fn):
            try:
                logger.info("[Plugin] Stopping %s (%s)…", plugin.name, plugin.__class__.__name__)
                stop_fn()
            except Exception as e:
                logger.warning("[Plugin] %s.stop() failed – %s", plugin.name, e)
