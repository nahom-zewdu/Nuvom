# `nuvom`

> 🧠 Lightweight, plugin-first task queue for Python. No Redis, Windows-native, AST-powered task discovery, and extensible by design.

![status](https://img.shields.io/badge/version-v0.9-blue)
![python](https://img.shields.io/badge/python-3.8%2B-yellow)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

---

## ✨ Why Nuvom?

Nuvom is a developer-first job execution engine that helps you queue, execute, and persist background tasks—without needing Redis, Celery, or any external services. Designed to be fully **Windows-compatible**, Nuvom favors **simplicity**, **smart defaults**, and **pluggable architecture** over complexity and vendor lock-in.

Key philosophies:

* 🪟 **Runs on Windows** (no Linux-only assumptions)
* 🔌 **Plugin-first**: easily extend queues, backends, task loaders
* ⚙️ **No Redis**, **no brokers**, and **no infrastructure**
* 📜 **AST-powered static task discovery** (no imports required)
* 📂 **Manifest caching** for blazing-fast CLI performance

---

## 🧠 Core Concepts

| Concept    | Description                                       |
| ---------- | ------------------------------------------------- |
| `@task`    | Decorator to register an executable function      |
| Job        | A serialized instance of a task to be executed    |
| Worker     | Thread that pulls and runs jobs from a queue      |
| Dispatcher | Orchestrates job dispatching and retries          |
| Backend    | Stores job results or errors                      |
| Registry   | Maps task names to callables and metadata         |
| Discovery  | Uses AST parsing to auto-discover all tasks       |
| CLI        | Full-featured developer CLI for control & insight |
| Plugins    | Dynamically loaded components to extend Nuvom     |

---

## 📦 Installation

> Nuvom is currently in active development. Until v1.0, install locally:

```bash
git clone https://github.com/nahom-zewdu/Nuvom
cd Nuvom
pip install -e .
```

### 🔧 Dependencies

* `rich`
* `typer`
* `pydantic-settings`
* `msgpack`

---

## ⚙️ Quickstart

### 1. Define a Task

```python
# tasks.py
from nuvom.task import task

@task(retries=2, retry_delay_secs=5, timeout_secs=3, store_result=True)
def add(x, y):
    return x + y
```

### 2. Queue a Job

```python
from tasks import add

job = add.delay(5, 7)
print(job.id)
```

### 3. Start the Worker Pool

```bash
nuvom runworker
```

### 4. Check Job Result

```bash
nuvom inspect job <job_id>
```

### 5. Check Result of Multiple Jobs

```bash
nuvom history recent --limit 10 --status SUCCESS
```

### 6. Retry a failed job (manual)

```python
from nuvom.sdk import retry_job
retry_job("<job_id>")
```

---

## 🚀 Features

* ✅ `@task()` decorator with `.delay()` and `.map()` support
* ✅ No import side-effects: AST-based task discovery
* ✅ Pluggable queue and result backends
* ✅ Rich-powered logging with tracebacks
* ✅ File and in-memory queue support
* ✅ Retry logic and lifecycle hooks
* ✅ Fast startup via task manifest cache
* ✅ CLI to list, discover, and inspect jobs
* ✅ `.env`-based configuration via `pydantic-settings`
* ✅ Retry delay and timeout control (`timeout_secs`, `retries`, `retry_delay_secs`)
* ✅ CLI to retry jobs, view full metadata, and browse job history
* ✅ Local dev runner to execute a job synchronously from JSON
* ✅ Plugin-first backend system — extend via `.nuvom_plugins.toml`
* ✅ Graceful shutdown lifecycle support for plugin-backed workers
* ✅ SQLite result backend with file-path configurability
* ✅ Built-in Prometheus plugin for runtime metrics (queue size, worker count, in-flight jobs)

---

## ⏱ Retry Delay + Timeout Policy

Nuvom v0.8 introduces full support for job retries and timeout policies with fine-grained control:

| Field             | Purpose                                               |
|-------------------|-------------------------------------------------------|
| `timeout_policy`  | Timeout-policy support to Job for runtime control on timeout behavior|
| `timeout_secs`    | Maximum time in seconds a job is allowed to run     |
| `retries`         | How many times to retry a job after failure          |
| `retry_delay_secs`| Wait time (in seconds) before retrying a failed job  |

If a job fails and `retries > 0`, depending on the timeout-policy it will be retried automatically after the specified delay. All retry attempts and tracebacks are recorded in metadata.

```python
@task(retries=2, timeout_policy='retry', retry_delay_secs=5, timeout_secs=3)
def unstable():
    raise RuntimeError("Oops")

enqueue(Job("unstable"))
```

---

## 🧪 CLI Overview

```bash
nuvom --help
```

| Command                       | Description                                                    |
| ----------------------------- | ------------------------------------------                     |
| `nuvom runworker`             | Start worker threads                                           |
| `nuvom status <id>`           | Get job result or error                                        |
| `nuvom list tasks`            | List all discovered `@task` functions                          |
| `nuvom discover tasks`        | Scan project and generate manifest                             |
| `nuvom config`                | Print current configuration                                    |
| `nuvom inspect job <id>`      | Inspect job result and metadata                                |
| `nuvom history recent`        | Inspect result of multiple jobs                                |
| `nuvom runtestworker run`     | Run job locally from JSON file                                 |
| `nuvom plugin test`           | Validate a plugin and run its `start/stop` hooks.              |
| `nuvom plugin status`         | Display all plugins that are registered                        |
| `nuvom plugin scaffold`       | Scaffold a new plugin stub that implements the Plugin protocol.|

---

## 🔧 Configuration

Nuvom loads settings from `.env` via `pydantic-settings`.

### Example `.env`

```env
NUVOM_ENVIRONMENT=dev|prod|test
NUVOM_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|
NUVOM_RESULT_BACKEND=file|memory
NUVOM_QUEUE_BACKEND=file|memory
NUVOM_SERIALIZATION_BACKEND=msgpack
NUVOM_MAX_WORKERS=4
NUVOM_BATCH_SIZE=10
NUVOM_JOB_TIMEOUT_SECS=30
NUVOM_MANIFEST_PATH=.nuvom/manifest.json
NUVOM_TIMEOUT_POLICY=fail|retry|ignore
NUVOM_PROMETHEUS_PORT=9160
```

---

### Plugin Configuration via `.nuvom_plugins.toml`

To enable Prometheus metrics, add the plugin to `.nuvom_plugins.toml`:

```toml
[plugins]
prometheus = ["nuvom.plugins.monitoring.prometheus:PrometheusPlugin"]
```

 You can override the default exporter port (defaults to 9150) in your .env

---

## 📚 Internals

### Task Discovery

* Parses files with AST to find `@task` decorators
* Skips `.nuvomignore` and filtered paths
* Writes results to `.nuvom/manifest.json`
* Loaded during runtime or via `nuvom discover tasks`

### Worker Execution

* Multi-threaded workers pull jobs in batches
* Jobs are executed with timeouts and retries
* Lifecycle hooks are respected: `before_job`, `after_job`, `on_error`
* On graceful shutdown, all active workers cleanly stop, flush logs, and exit safely
* Plugin-based workers also receive lifecycle events for teardown

### Backends

* Memory and file-based backends
* Fully pluggable via interface (`BaseJobQueue`, `BaseResultBackend`)
* Plugins can register new queue or result backends via `.nuvom_plugins.toml`
* SQLite backend uses on-disk persistence with a compact schema and fast queries

## 📈 Prometheus Monitoring Plugin

Nuvom comes with a built-in Prometheus plugin to expose live worker and queue metrics for observability and alerting.

### Metrics Exposed

| Metric Name           | Description                          |
|-----------------------|--------------------------------------|
| `nuvom_worker_count`  | Number of active worker threads      |
| `nuvom_inflight_jobs` | Number of jobs currently executing   |
| `nuvom_queue_size`    | Current number of jobs in the queue  |

### How it Works

Once enabled, the Prometheus plugin runs a lightweight HTTP server exposing metrics at:

`http://localhost:<port>/metrics`

It scrapes runtime data from the dispatcher via a live `metrics_provider` hook.

### Debug Page

You can also visit:
`http://localhost:<port>/`

to see a human-friendly info page confirming the exporter is running.

---

## 🧩 Architecture Diagram

```text
    +---------------------+
    |    @task decorator  |
    +---------------------+
               |
               v
    +---------------------+        +---------------------+
    |    Task Registry    |<-----> |  Manifest Manager   |
    +---------------------+        +---------------------+
               |                               |
               v                               v
    +---------------------+        +---------------------+
    |     Dispatcher      |------> |   Queue Backend     |
    +---------------------+        +---------------------+
               |                               |
               v                               v
          +-----------+                +------------------+
          |  Worker   |--------------->|   Job Runner     |
          +-----------+                +------------------+
                                                 |
                                                 v
                                     +--------------------------+
                                     |   Result Backend (Mem)   |
                                     +--------------------------+
```

---

## 🛠 Extending Nuvom

Example: Registering a custom result backend plugin

```python
from nuvom.plugins.contracts import Plugin

class MyResultBackend:
    def set_result(...): ...
    def get_result(...): ...
    def set_error(...): ...
    def get_error(...): ...

class MyPlugin(Plugin):
    api_version = "<version>"
    name = "my_plugin"
    provides = ["result_backend"]

    def start(self, settings):
        from nuvom.plugins.registry import register_result_backend
        register_result_backend("my_backend", MyResultBackend)

    def stop(self): pass
```

Add it to `.nuvom_plugins.toml`:

```toml
[plugins]
result_backend = ["my_plugin:MyPlugin"]
```

---

## 📁 Project Layout

``` text
nuvom/
├── cli/                 # Typer-based CLI commands
├── config.py            # .env configuration manager
├── discovery/           # Task discovery, parsing, manifest
├── execution/           # JobRunner + execution logic
├── queue_backends/      # File & memory queues
├── result_backends/     # Pluggable result stores
├── registry/            # Task registry singleton
├── plugins/             # Nuvom plugins' loader, registr and contracts
├── task.py              # Task decorator logic
├── worker.py            # Threaded worker pool, Task dispatching and retries
├── utils/               # File ops, serializers, etc.
├── log.py               # Rich-based logger
├── watcher.py           # Watches manifest file for changes and reloads tasks into the registry
```

---

## 🛣️ Nuvom Roadmap

Feature progression and version intentions for Nuvom.
Versions are milestone-based — not strictly semver.

---

## ✅ v0.1 — Core Foundations

* [x] Minimal `@task` decorator and delay mechanism
* [x] In-memory task queue
* [x] Threaded worker pool execution

---

## ✅ v0.2 — Result Backends & CLI

* [x] Pluggable result backend architecture
* [x] Memory and file-based result stores
* [x] CLI (`nuvom runworker`) to start worker threads
* [x] Job polling via `pop_batch()` with batching

---

## ✅ v0.3 — Pluggable Queues

* [x] Queue backends: `MemoryJobQueue`, `FileJobQueue`
* [x] Batch-aware dequeuing with fallback
* [x] Corrupt job quarantine support (`.corrupt` file handling)
* [x] `.msgpack` based serialization
* [x] Concurrency stress tests & safe multi-thread file locks

---

## ✅ v0.4 — Execution Runtime & Lifecycle Hooks

* [x] Job execution via `ExecutionEngine` abstraction
* [x] Runtime configuration: timeouts, batch size, max workers
* [x] Job metadata injection (`job.retries_left`, `created_at`, etc.)
* [x] Lifecycle hook support: `before_job`, `after_job`, `on_error`
* [x] Retry-on-failure system with max attempt logic

---

## ✅ v0.5 — Static Task Discovery & Registry

* [x] AST-based task scanning with `@task` decorator detection
* [x] Recursive file walker with `.nuvomignore` support
* [x] Pathspec-based include/exclude filtering (like `.gitignore`)
* [x] Manifest system: caching parsed tasks with file hashes
* [x] CLI: `nuvom discover tasks` to scan & update manifest
* [x] Dynamic task loader via module or fallback to file path
* [x] Auto-registration from manifest at worker startup
* [x] Centralized thread-safe registry with duplicate control (`force`, `silent`, default=error)
* [x] CLI: `nuvom tasks list` with metadata

---

### ✅ v0.6

* [x] Dynamic dispatching assigns jobs to the least busy worker, maximizing throughput and minimizing wait time.
* [x] Tag and describe tasks directly in your code, then explore them with `nuvom list tasks`.
* [x] Use `--dev` to auto-refresh your task registry on code or manifest changes—no need to restart workers.
* [x] See colorful, structured logs and tracebacks that make debugging easier and faster.
* [x] Manifest updates apply seamlessly during worker runtime.
* [x] Manifest diffs, detailed task listings, and more—all powered by Rich.
* [x] Robust error handling

---

### ✅ v0.7

Nuvom now has first-class observability:

* [x] Tracebacks and rich metadata
* [x] CLI inspection tools
* [x] Historical job queries
* [x] Designed for both dev and production debugging

---

### ✅ v0.8  Reliability & DX Polish

* [x] Retry System   Retry-on-failure, retry limits, delay support
* [x] Timeouts       Per-job timeout and termination
* [x] Observability  Tracebacks in CLI and SDK, job attempt metadata
* [x] CLI Polish     `runtestworker`, formatted output modes, job history
* [x] SDK Tools      `retry_job()` for re-enqueuing failed jobs
* [x] Docs           Full README update for all new features

---

### ✅ v0.9 — Plugin Architecture & SQLite

* [x] Plugin-first backend architecture with `.nuvom_plugins.toml`
* [x] Graceful worker shutdown (plugin-aware lifecycle teardown)
* [x] SQLite result backend (structured schema + full metadata)
* [x] Test coverage and registry updates for plugin-based backends
* [x] Clean logging and startup behavior for dynamic backends

---

## 🧪 Future (Backlog Ideas)

* [ ] Redis & SQLite queue backends
* [ ] DAG/task chaining support (like `job1.then(job2)`)
* [ ] Task versioning & signature validation
* [ ] Built-in dashboards & Prometheus metrics
* [ ] Distributed execution (multi-host worker mesh)
* [ ] Static `.nuvom_tasks.json` export for zero-import startup
* [ ] VSCode extension: visual queue monitor, task explorer

---

## 🧠 Philosophy

We believe tools should be:

* 🔧 Easy to extend
* 🪶 Light on assumptions
* 🪟 Friendly for Windows and cross-platform devs
* 🧠 Predictable and observable

---

## 👥 Contributing

Pull requests are welcome! See [`ARCHITECTURE`](docs/architecture.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) to get started.

---

## 🪪 License

Apache 2.0 — use it freely, build responsibly.

---
