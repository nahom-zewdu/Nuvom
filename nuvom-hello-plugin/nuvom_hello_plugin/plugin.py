# nuvom-hello-plugin/nuvom_hello_plugin/plugin.py

from nuvom.plugins.contracts import Plugin


class DummyResultBackend:
    def set_result(self, *args, **kwargs): print("✅ Dummy result saved")

    def get_result(self, job_id): return {"dummy": True, "job_id": job_id}

    def set_error(self, *args, **kwargs): print("❌ Dummy error recorded")

    def get_error(self, job_id): return {"error": "DummyError", "job_id": job_id}


class HelloPlugin(Plugin):
    api_version = "1.0"
    name = "hello_plugin"
    provides = ["result_backend"]

    def start(self, settings: dict) -> None:
        from nuvom.plugins.registry import register_result_backend
        register_result_backend("dummy", DummyResultBackend)

    def stop(self) -> None:
        print(f"{self.provides[0]} stopped")
