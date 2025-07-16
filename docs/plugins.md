# Plugin System

Nuvom v0.9 introduced first-class plugin support — allowing developers to register their own backends, extensions, and instrumentation layers with clean lifecycle management.

---

## 🔌 What is a Plugin?

A **plugin** is a Python class that implements the `Plugin` protocol, defining:

- `name`: Unique plugin name
- `provides`: What kind of capability it offers (e.g. `queue_backend`, `monitoring`)
- `start(settings: dict)`: Initialization logic
- `stop()`: Cleanup logic on shutdown

---

## 📁 File Layout

Plugins can live inside your project or in external libraries. Common layout:

```text
my_project/
├── plugins/
│   ├── my_plugin.py       # Your plugin logic
│   └── __init__.py
└── .nuvom_plugins.toml    # Plugin registration
````

---

## 🧱 Plugin Example: Custom Queue Backend

```python
# plugins/my_queue.py
from nuvom.queue_backends.base import BaseJobQueue
from nuvom.plugins.contracts import Plugin

class MyQueue(BaseJobQueue):
    def enqueue(self, job): ...
    def dequeue(self, timeout=None): ...
    def pop_batch(self, n): ...
    def qsize(self): ...
    def clear(self): ...

class MyPlugin(Plugin):
    name = "my_queue"
    provides = ["queue_backend"]

    def start(self, settings):
        from nuvom.plugins.registry import register_queue_backend
        register_queue_backend("my_custom_queue", MyQueue)

    def stop(self):
        pass
```

Then register in `.nuvom_plugins.toml`:

```toml
[plugins]
queue_backend = ["plugins.my_queue:MyPlugin"]
```

---

## 🗃 Plugin Registry

Nuvom loads plugins at **worker startup** (not during CLI commands).

Each plugin is discovered from `.nuvom_plugins.toml`, instantiated, and injected with runtime settings.

To test plugin loading:

```bash
nuvom plugin test
nuvom plugin list
nuvom plugin inspect my_queue
```

---

## 🛠 Plugin Lifecycle

Each plugin receives a `start(settings)` call when the worker starts.

Example use cases:

- Registering new backends
- Spawning monitoring threads
- Configuring metrics exporters
- Connecting to databases

On shutdown (`CTRL+C`, SIGINT), plugins receive a `stop()` call to clean up.

---

## 🧪 Plugin Types

| Provides         | Purpose                                  |
| ---------------- | ---------------------------------------- |
| `queue_backend`  | Add a new job queue implementation       |
| `result_backend` | Add a result/error store                 |
| `monitoring`     | Expose runtime metrics (e.g. Prometheus) |
| `lifecycle_hook` | Run logic on job events (future)         |

---

## 📊 Monitoring Plugin Example

```python
# plugins/prometheus_exporter.py
from nuvom.plugins.contracts import Plugin
from nuvom.plugins.registry import register_metrics_provider

class PrometheusPlugin(Plugin):
    name = "prometheus"
    provides = ["monitoring"]

    def start(self, settings):
        from my_exporter import run_exporter
        run_exporter(port=settings.get("prometheus_port", 9150))

    def stop(self):
        ...
```

---

## 🧠 Best Practices

- Keep plugins self-contained.
- Use `settings` from `.env` or custom sources.
- Fail fast if required dependencies are missing.
- Avoid blocking inside `start()` — spawn threads if needed.
- Don’t forget `stop()` for graceful cleanup.

---

## 🚦 CLI Support

| Command                | Description                   |
| ---------------------- | ----------------------------- |
| `nuvom plugin test`    | Validates and loads plugins   |
| `nuvom plugin list`    | Lists registered plugin types |
| `nuvom plugin inspect` | Shows metadata for one plugin |

---

## 🚧 Roadmap (Future Plugin Hooks)

| Feature                      | Status                    |
| ---------------------------- | ------------------------- |
| `before_job`, `after_job`    | \[ ] Planned (via plugin) |
| `metrics_provider` interface | ✅ Prometheus supported    |
| CLI plugin extensions        | \[ ] Future               |
| Multi-process plugin runners | \[ ] Future               |

---

## 🧩 Summary

Plugins allow you to:

- Add new backends (queue, result)
- Hook into Nuvom’s lifecycle
- Export runtime metrics
- Customize behavior without modifying Nuvom core

> Plugins make Nuvom truly pluggable. Add what you need — nothing more.
