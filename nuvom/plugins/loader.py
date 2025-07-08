# nuvom/plugins/loader.py

"""
Hybrid plugin loader (back‑compatible with v0.8).

Discovery order
---------------
1. Python entry‑points in the ``nuvom`` group
2. ``.nuvom_plugins.toml`` (legacy + capability‑specific keys)

Accepted plugin shapes
----------------------
• Class **sub‑classing** :class:`nuvom.plugins.contracts.Plugin`
• Class that merely **duck‑types** the contract
• Legacy callable ``register()`` (DEPRECATED — emits warning)
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import tomllib
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Set

from nuvom.log import get_logger
from nuvom.plugins.contracts import API_VERSION, Plugin
from nuvom.plugins.registry import REGISTRY

# --------------------------------------------------------------------------- #
# Globals
# --------------------------------------------------------------------------- #
_TOML_PATH = Path(".nuvom_plugins.toml")
_LOADED: Set[str] = set()       # memoised "module[:attr]" specs
LOADED_PLUGINS: Set[Plugin] = set()   # instantiated plugin objects
logger = get_logger()

# --------------------------------------------------------------------------- #
# Discovery helpers
# --------------------------------------------------------------------------- #
def _toml_targets() -> list[str]:
    """
    Collect *every* dotted‑path string from `.nuvom_plugins.toml`.

    Supported layouts
    -----------------
    Legacy:
        [plugins]
        modules = ["pkg.mod", "pkg.other:Class"]

    Capability keys (preferred):
        [plugins]
        queue_backend  = ["pkg.q:MyQ"]
        result_backend = ["pkg.r:MyR"]
    """
    if not _TOML_PATH.exists():
        return []

    try:
        data = tomllib.loads(_TOML_PATH.read_text("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        logger.error("[Plugins] Invalid TOML in %s – %s", _TOML_PATH, exc)
        return []

    plugin_block = data.get("plugins", {})
    targets: list[str] = []

    # 1) legacy
    targets.extend(plugin_block.get("modules", []))

    # 2) every other list under [plugins]
    for key, value in plugin_block.items():
        if key != "modules" and isinstance(value, list):
            targets.extend(value)

    return targets


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
# Import & helper utils
# --------------------------------------------------------------------------- #
def _import_target(spec: str) -> Any:
    """
    Import ``"package.module:attr"`` or bare ``"package.module"`` and return
    the attribute (class/function) or the module object.
    """
    mod_path, _, attr = spec.partition(":")
    module: ModuleType = importlib.import_module(mod_path)
    return getattr(module, attr) if attr else module


def _is_duck_plugin(cls: type) -> bool:
    """True if *cls* has all required Plugin attributes / methods."""
    required = ("api_version", "name", "provides", "start", "stop")
    return all(hasattr(cls, attr) for attr in required)


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
    settings:
        Optional per‑plugin configuration passed to ``plugin.start()``.
    """
    if _LOADED:        # already done in this process
        return

    cfg = settings or {}

    for spec in _iter_targets():
        if spec in _LOADED:
            continue

        try:
            target = _import_target(spec)

            # ───────────────────────── Legacy callable path ────────────────────
            if callable(target) and not isinstance(target, type):
                warnings.warn(
                    "Legacy plugin register() style is deprecated and will be "
                    "removed in Nuvom 1.0. Implement the Plugin protocol.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                target()                         # run register()
                logger.info("[Plugin‑Legacy] %s loaded", spec)
                _LOADED.add(spec)
                continue

            # ───────────────────────── Class path ──────────────────────────────
            if isinstance(target, type):
                try:
                    subclass_ok = issubclass(target, Plugin)
                except TypeError:                # Protocol w/ data attrs
                    subclass_ok = False

                if not (subclass_ok or _is_duck_plugin(target)):
                    logger.warning("[Plugin] %s does not implement Plugin protocol", spec)
                    continue

                plugin_cls = target

                # Major‑version gate
                if _major_mismatch(API_VERSION, plugin_cls.api_version):
                    logger.error(
                        "[Plugin] %s api_version %s incompatible with core %s",
                        plugin_cls.__name__, plugin_cls.api_version, API_VERSION,
                    )
                    continue

                plugin: Plugin = plugin_cls()  # type: ignore[assignment]
                plugin.start(cfg.get(plugin.name, {}))
                LOADED_PLUGINS.add(plugin)

                REGISTRY.register(plugin.provides[0], plugin.name, plugin, override=True)
                logger.info("[Plugin] %s (%s) loaded", plugin.name, plugin_cls.__name__)

                _LOADED.add(spec)
                continue

            # ───────────────────────── Unknown artefact ────────────────────────
            logger.warning("[Plugin] %s does not expose a Plugin or register()", spec)

        except Exception as exc:   # noqa: BLE001 – we want broad capture for logging
            logger.exception("[Plugin] Failed to load %s – %s", spec, exc)

    # Memoise built‑ins that are Plugin instances (rare but possible)
    for cap in ("queue_backend", "result_backend"):
        for name, obj in REGISTRY._caps.get(cap, {}).items():
            if isinstance(obj, Plugin) and name not in _LOADED:
                _LOADED.add(name)

def shutdown_plugins() -> None:
    """Call .stop() on all loaded plugins (if defined)."""
    for plugin in LOADED_PLUGINS:
        stop_fn = getattr(plugin, "stop", None)
        if callable(stop_fn):
            try:
                logger.info("[Plugin] Stopping %s (%s)...", plugin.name, plugin.__class__.__name__)
                stop_fn()
            except Exception as e:
                logger.warning("[Plugin] %s.stop() failed – %s", plugin.name, e)
