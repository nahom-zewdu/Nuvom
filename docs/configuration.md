# Nuvom Configuration Guide

Nuvom is highly configurable using environment variables and `.env` files. This guide explains all supported settings, how they affect runtime behavior, and how to configure plugins.

---

## 📁 Where Settings Come From

Nuvom loads configuration from:

1. `.env` file in your project root (uses `pydantic-settings`)
2. Environment variables (`export FOO=...`)
3. Defaults defined in code (if no value is provided)

---

## 🗃 Example `.env`

```env
NUVOM_ENVIRONMENT=dev
NUVOM_LOG_LEVEL=INFO
NUVOM_QUEUE_BACKEND=file
NUVOM_RESULT_BACKEND=memory
NUVOM_SERIALIZATION_BACKEND=msgpack
NUVOM_MAX_WORKERS=4
NUVOM_BATCH_SIZE=10
NUVOM_JOB_TIMEOUT_SECS=30
NUVOM_MANIFEST_PATH=.nuvom/manifest.json
NUVOM_TIMEOUT_POLICY=retry
NUVOM_PROMETHEUS_PORT=9150
NUVOM_SQLITE_QUEUE_PATH=.nuvom/queue.db
NUVOM_SQLITE_RESULT_PATH=.nuvom/results.db
````

---

## ⚙️ Core Configuration Variables

| Variable                      | Description                                              | Default                |
| ----------------------------- | -------------------------------------------------------- | ---------------------- |
| `NUVOM_ENVIRONMENT`           | `dev`, `test`, or `prod`                                 | `dev`                  |
| `NUVOM_LOG_LEVEL`             | Logging level: `DEBUG`, `INFO`, etc.                     | `INFO`                 |
| `NUVOM_QUEUE_BACKEND`         | Backend type: `memory`, `file`, or plugin name           | `memory`               |
| `NUVOM_RESULT_BACKEND`        | Result store: `memory`, `file`, `sqlite`, or plugin name | `memory`               |
| `NUVOM_SERIALIZATION_BACKEND` | Format: `msgpack` (others in future)                     | `msgpack`              |
| `NUVOM_MANIFEST_PATH`         | Task discovery manifest path                             | `.nuvom/manifest.json` |
| `NUVOM_JOB_TIMEOUT_SECS`      | Default job timeout (if not overridden in `@task`)       | `30`                   |
| `NUVOM_BATCH_SIZE`            | Jobs pulled at once per worker cycle                     | `10`                   |
| `NUVOM_MAX_WORKERS`           | Number of worker threads to spawn                        | `4`                    |
| `NUVOM_TIMEOUT_POLICY`        | Behavior on timeout: `retry`, `fail`, `ignore`           | `retry`                |

---

## 🧩 Plugin Configuration

Plugins are registered via `.nuvom_plugins.toml` in the root of your project.

```toml
[plugins]
queue_backend = ["my_module:MyQueuePlugin"]
result_backend = ["my_module:MyResultPlugin"]
monitoring = ["nuvom.plugins.monitoring.prometheus:PrometheusPlugin"]
```

Use your `.env` to pass any plugin-specific values:

```env
NUVOM_PROMETHEUS_PORT=9150
MY_PLUGIN_AUTH_TOKEN=abc123
```

Inside the plugin, access them via the `settings` argument passed to `start()`:

```python
def start(self, settings):
    port = settings.get("prometheus_port", 9150)
```

---

## 🧠 SQLite Backend Settings

If you use the SQLite queue or result backend, configure paths:

| Variable                   | Purpose                             | Default             |
| -------------------------- | ----------------------------------- | ------------------- |
| `NUVOM_SQLITE_QUEUE_PATH`  | SQLite file path for the job queue  | `.nuvom/queue.db`   |
| `NUVOM_SQLITE_RESULT_PATH` | SQLite file path for result backend | `.nuvom/results.db` |

Ensure the directories exist or Nuvom will create them automatically.

---

## 🧪 CLI to View Active Config

You can inspect current config at any time:

```bash
nuvom config
```

Output:

```text
Environment: dev
Queue Backend: file
Result Backend: sqlite
Max Workers: 4
Batch Size: 10
Manifest Path: .nuvom/manifest.json
...
```

---

## 🔐 Best Practices

* Commit a `.env.example` file for contributors
* Don’t hardcode secrets or plugin tokens
* Keep `.env` out of version control (`.gitignore`)
* Use `dotenv` or OS environment overrides in CI/CD

---

## 🧩 Summary

Nuvom gives you full control over how it runs, queues jobs, stores results, and loads plugins — all through a clean `.env` and TOML-based system.

You can:

* Swap backends without changing code
* Override runtime behavior with simple settings
* Pass config to your own plugins
* Use the CLI to verify current values

> Simple configs. Powerful control.
