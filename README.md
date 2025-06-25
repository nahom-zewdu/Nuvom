# `nuvom`

> 🧠 Lightweight, plugin-first task queue for Python. No Redis, Windows-native, AST-powered task discovery, and extensible by design.

![status](https://img.shields.io/badge/version-v0.6-blue)
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

---

## 📦 Installation

> Nuvom is currently in active development. Until v1.0, install locally:

```bash
git clone https://github.com/your-org/nuvom
cd nuvom
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

@task(retries=2, store_result=True)
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

### 4. Check Result of Multiple Jobs

```bash
nuvom history recent --limit 10 --status SUCCESS
```

---

## 🚀 Features

✅ `@task()` decorator with `.delay()` and `.map()` support
✅ No import side-effects: AST-based task discovery
✅ Pluggable queue and result backends
✅ Rich-powered logging with tracebacks
✅ File and in-memory queue support
✅ Retry logic and lifecycle hooks
✅ Fast startup via task manifest cache
✅ CLI to list, discover, and inspect jobs
✅ `.env`-based configuration via `pydantic-settings`

---

## 🧪 CLI Overview

```bash
nuvom --help
```

| Command                | Description                           |
| ---------------------- | ------------------------------------- |
| `nuvom runworker`      | Start worker threads                  |
| `nuvom status <id>`    | Get job result or error               |
| `nuvom list tasks`     | List all discovered `@task` functions |
| `nuvom discover tasks` | Scan project and generate manifest    |
| `nuvom config`         | Print current configuration           |
| `nuvom inspect job <job_id>`| Inspect job result               |
| `nuvom history recent` | Inspect result of multiple jobs       |

---

## 🔧 Configuration

Nuvom loads settings from `.env` via `pydantic-settings`.

### Example `.env`

```env
NUVOM_ENVIRONMENT=dev
NUVOM_LOG_LEVEL=DEBUG
NUVOM_RESULT_BACKEND=file
NUVOM_QUEUE_BACKEND=file
NUVOM_MAX_WORKERS=4
NUVOM_BATCH_SIZE=10
NUVOM_JOB_TIMEOUT_SECS=30
NUVOM_MANIFEST_PATH=.nuvom/manifest.json
```

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

### Backends

* Memory and file-based backends
* Fully pluggable via interface (`BaseJobQueue`, `BaseResultBackend`)

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

Add your own backend:

```python
from nuvom.queue_backends.base import BaseJobQueue

class MyCustomQueue(BaseJobQueue):
    def enqueue(self, job): ...
    def dequeue(self, timeout=1): ...
    ...
```

Then configure it via `.env` or code.

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
├── task.py              # Task decorator logic
├── worker.py            # Threaded worker pool, Task dispatching and retries
├── utils/               # File ops, serializers, etc.
├── log.py               # Rich-based logger
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
