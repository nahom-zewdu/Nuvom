# nuvom/registry/auto_register.py

"""
Auto-registration logic for loading discovered tasks from manifest
and injecting them into the global task registry.
"""

from nuvom.discovery.manifest import ManifestManager
from nuvom.discovery.loader import load_task
from nuvom.registry.registry import get_task_registry
from nuvom.log import logger


def auto_register_from_manifest(manifest_path: str = None):
    """
    Auto-register all discovered tasks from the manifest into the global task registry.

    Args:
        manifest_path (str, optional): Path to the manifest file.
                                       If None, the default path is used.

    Loads the manifest, dynamically imports each task function,
    and registers it into the registry with `force=True`.

    Logs failures and reports successful registrations.
    """
    manifest = ManifestManager(manifest_path)
    discovered_tasks = manifest.load()
    registry = get_task_registry()

    for ref in discovered_tasks:
        try:
            func = load_task(ref)
            registry.register(ref.func_name, func, force=True)
            logger.debug(f"[auto-register] ✅ Registered task '{ref.func_name}' from {ref.module_name}")
        except Exception as e:
            logger.warning(f"[auto-register] ❌ Failed to load task '{ref.func_name}' from {ref.module_name}: {e}")

    logger.info(f"[auto-register] Registered tasks: {list(registry.all().keys())}")
