# nuvom-hello-plugin/nuvom_hello_plugin/plugin.py

from nuvom.plugins.contracts import Plugin

class HelloPlugin(Plugin):
    api_version = "1.0"
    name = "hello"
    provides = ["queue_backend"]
    requires = []

    def start(self, settings: dict) -> None:
        print("[HelloPlugin] start() called with:", settings)

    def stop(self) -> None:
        print("[HelloPlugin] stop() called")
