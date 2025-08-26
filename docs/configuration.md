# Nuvom Configuration Guide

Nuvom is fully configurable via environment variables and `.env` files. This guide explains supported settings, how they affect runtime behavior, and plugin integration, including the scheduler backend.

---

## Where Settings Come From

Nuvom loads configuration in order of precedence:

1. `.env` file in your project root (via `pydantic-settings`)
2. Environment variables (`export FOO=...`)
3. Defaults defined in code if not overridden

---

## Example `.env`

```env
NUVOM_QUEUE_BACKEND=file
NUVOM_RESULT_BACKEND=memory
NUVOM_SERIALIZATION_BACKEND=msgpack
NUVOM_SCHEDULER_BACKEND=file

NUVOM_ENVIRONMENT=dev
NUVOM_LOG_LEVEL=INFO

NUVOM_MAX_WORKERS=4
NUVOM_BATCH_SIZE=10
NUVOM_JOB_TIMEOUT_SECS=30
NUVOM_TIMEOUT_POLICY=retry

NUVOM_MANIFEST_PATH=.nuvom/manifest.json
NUVOM_SQLITE_QUEUE_PATH=.nuvom/queue.db
NUVOM_SQLITE_RESULT_PATH=.nuvom/results.db
```

---

## Core Configuration Variables

| Variable                      | Description                                                   | Default                |
| ----------------------------- | ------------------------------------------------------------- | ---------------------- |
| `NUVOM_ENVIRONMENT`           | `dev`, `test`, or `prod`                                      | `dev`                  |
| `NUVOM_LOG_LEVEL`             | Logging level: `DEBUG`, `INFO`, etc.                          | `INFO`                 |
| `NUVOM_QUEUE_BACKEND`         | Backend type: `memory`, `file`, `sqlite`, or plugin name      | `sqlite`               |
| `NUVOM_RESULT_BACKEND`        | Result store: `memory`, `file`, `sqlite`, or plugin name      | `sqlite`               |
| `NUVOM_SERIALIZATION_BACKEND` | Format for job payloads (`msgpack`)                           | `msgpack`              |
| `NUVOM_MANIFEST_PATH`         | Path to task discovery manifest                               | `.nuvom/manifest.json` |
| `NUVOM_JOB_TIMEOUT_SECS`      | Default job timeout (unless overridden in `@task`)            | `30`                   |
| `NUVOM_BATCH_SIZE`            | Jobs pulled per worker cycle                                  | `10`                   |
| `NUVOM_MAX_WORKERS`           | Number of worker threads                                      | `4`                    |
| `NUVOM_TIMEOUT_POLICY`        | Behavior on timeout: `retry`, `fail`, `ignore`                | `retry`                |
| `NUVOM_SCHEDULER_BACKEND`     | Scheduler backend to use (`memory`, `redis`, `sqlite`, plugin) | `sqlite`               |

---

## Plugin Configuration

Plugins extend Nuvom dynamically and are registered via `.nuvom_plugins.toml`:

```toml
[plugins]
queue_backend = ["my_module:MyQueuePlugin"]
result_backend = ["my_module:MyResultPlugin"]
scheduler_backend = ["my_module:CustomSchedulerBackend"]
monitoring = ["nuvom.plugins.monitoring.prometheus:PrometheusPlugin"]
```

Pass plugin-specific values via `.env`:

```env
MY_PLUGIN_AUTH_TOKEN=abc123
```

Inside the plugin, access them via the `settings` argument passed to `start()`:

```python
def start(self, settings):
    token = settings.get("auth_token", None)
```

---

## SQLite Backend Settings

For SQLite backends:

| Variable                   | Purpose                             | Default             |
| -------------------------- | ----------------------------------- | ------------------- |
| `NUVOM_SQLITE_QUEUE_PATH`  | SQLite file path for job queue      | `.nuvom/queue.db`   |
| `NUVOM_SQLITE_RESULT_PATH` | SQLite file path for result backend | `.nuvom/results.db` |

Directories are created automatically if missing.

---

## CLI to View Active Config

```bash
nuvom config
```

Example output:

```text
Environment: dev
Queue Backend: sqlite
Result Backend: sqlite
Scheduler Backend: sqlite
Max Workers: 4
Batch Size: 10
Manifest Path: .nuvom/manifest.json
...
```

---

## Best Practices

* Commit `.env.example` for contributors
* Keep secrets out of version control (`.gitignore`)
* Override values in CI/CD via environment variables
* Use scheduler backends that match your production workload
* Verify configuration with `nuvom config`

---

## Summary

Nuvom gives developers clean, predictable, and extensible control over runtime behavior, queuing, results, plugins, and scheduling via a single scheduler backend variable.

> Developer-first, predictable, and professional configuration.

---
