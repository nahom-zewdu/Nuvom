# nuvom/plugins/loader.py

"""
Lightweight plugin loader.

Reads `.nuvom_plugins.toml` (if present) and imports listed modules.
Each plugin can either:
    • expose a `register()` function
    • perform registration at import time
"""

import importlib
import tomllib
from pathlib import Path
from types import ModuleType
from typing import List, Sequence

from nuvom.log import logger

_PLUGINS_LOADED: List[str] = []
_CONFIG_PATH = Path(".nuvom_plugins.toml")


def _load_config() -> Sequence[str]:
    if not _CONFIG_PATH.exists():
        logger.debug("[Plugins] No .nuvom_plugins.toml found – skipping plugin load")
        return []

    try:
        data = tomllib.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        logger.error("[Plugins] Invalid TOML in %s: %s", _CONFIG_PATH, exc)
        return []

    return list(data.get("plugins", {}).get("modules", []))


def load_plugins() -> None:
    """
    Import all plugin modules once per process. Safe to call multiple times.
    """
    if _PLUGINS_LOADED:
        return

    modules = _load_config()
    for mod_path in modules:
        try:
            module: ModuleType = importlib.import_module(mod_path)
            if hasattr(module, "register"):
                module.register()
            _PLUGINS_LOADED.append(mod_path)
            logger.info("[Plugins] Loaded %s", mod_path)
        except Exception as exc:
            logger.exception("[Plugins] Failed to load %s: %s", mod_path, exc)
