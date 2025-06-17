# nuvom/watcher.py

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread
from pathlib import Path
from rich import print

from nuvom.discovery.manifest import ManifestManager
from nuvom.discovery.loader import load_task
from nuvom.registry.registry import get_task_registry
from nuvom.registry.auto_register import auto_register_from_manifest

class ManifestChangeHandler(FileSystemEventHandler):
    """
    Watches the Nuvom manifest file for changes and reloads tasks into the registry
    on-the-fly during --dev mode.
    """
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path.resolve()

    def on_modified(self, event):
        if Path(event.src_path).resolve() == self.manifest_path:
            print("[yellow]🔁 Manifest updated — reloading tasks...[/yellow]")
            try:
                auto_register_from_manifest()
                print("[green]✅ Tasks reloaded.[/green]")
            except Exception as e:
                print(f"[red]🔥 Reload error:[/red] {e}")
