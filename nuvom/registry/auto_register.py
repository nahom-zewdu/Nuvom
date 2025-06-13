# nuvom/registry/auto_register.py

from nuvom.discovery.manifest import ManifestManager
from nuvom.discovery.loader import load_task
from nuvom.registry.registry import get_task_registry


def auto_register_from_manifest(manifest_path: str = None):
    """
    Auto-register all discovered tasks from the manifest into the global task registry.
    """
    
    manifest = ManifestManager(manifest_path)
    discovered_tasks = manifest.load()
    registry = get_task_registry()
    for ref in discovered_tasks:
        try:
            func = load_task(ref)
            registry.register(ref.func_name, func)
        except Exception as e:
            print(f"[warn] Failed to load task '{ref.func_name}' from {ref.module_name}: {e}")
    
    print(registry.all()) 