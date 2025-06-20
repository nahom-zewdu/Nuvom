# Nuvom — A Lightweight Python Task Queue (v0.5)

![status](https://img.shields.io/badge/version-v0.5-blue)
![python](https://img.shields.io/badge/python-3.8%2B-yellow)
![license](http://www.apache.org/licenses/)

**Nuvom** is a lightweight, developer-first task queue for Python designed for high performance, extensibility, and ease of use. It features pluggable result backends, recursive task auto-discovery with AST parsing, efficient job execution, CLI integration, and a robust runtime built for scaling and debugging.

---

## 🔥 Features

* ✅ Background task registration with `.delay()` and `.map()`
* ✅ Recursive AST-based task auto-discovery across projects (no imports needed)
* ✅ Persistent task manifest caching (`.nuvom_manifest.json`) for fast CLI operations
* ✅ Thread-safe singleton task registry with duplicate detection
* ✅ Worker pool with batch fetching and graceful shutdown
* ✅ Configurable result backends: memory, file (and planned Redis/SQLite)
* ✅ Retry logic and job lifecycle hooks (`before_job`, `after_job`, `on_error`)
* ✅ Rich CLI tooling for task discovery, listing, worker control, and job inspection
* ✅ `.env`-based configuration with `pydantic-settings`
* ✅ Minimal dependencies, no external service requirements

---

## 🚀 Getting Started

### 1. Install

```bash
pip install -e .
```

Dependencies: `rich`, `typer`, `pydantic-settings`.

### 2. Define a Task

```python
# tasks.py
from nuvom.task import task

@task(retries=3, store_result=True)
def add(x, y):
    return x + y
```

### 3. Submit a Job

```python
# main.py
from tasks import add

job = add.delay(2, 3)
print(f"Job queued with ID: {job.id}")
```

### 4. List Discovered Tasks

```bash
nuvom list tasks            # Uses cached manifest
nuvom discover tasks  # scans project recursively and builds manifest
```

### 5. Start the Worker Pool

```bash
nuvom runworker
```

### 6. Check Job Status

```bash
nuvom status <job-id>
```

---

## ⚙️ Configuration

Nuvom loads settings from `.env` files via `pydantic-settings`.

### 🔧 Sample `.env`

```env
NUVOM_ENVIRONMENT=dev
NUVOM_LOG_LEVEL=INFO
NUVOM_RESULT_BACKEND=file
NUVOM_MAX_WORKERS=4
NUVOM_BATCH_SIZE=10
NUVOM_JOB_TIMEOUT_SECS=60
NUVOM_QUEUE_MAXSIZE=0
NUVOM_MANIFEST_PATH=.nuvom_manifest.json
```

### 📖 `NUVOM_RESULT_BACKEND` Options

| Value    | Description                                  |
| -------- | -------------------------------------------- |
| `memory` | In-memory (fast, ephemeral)                  |
| `file`   | File-based persistent storage                |
| `redis`  | \[Planned] Production-grade persistent store |
| `sqlite` | \[Planned] Embedded persistent store         |

---

## 🧪 CLI Commands

```bash
nuvom --help
```

| Command                | Description                                         |
| ---------------------- | --------------------------------------------------- |
| `config`               | Show current configuration loaded from `.env`       |
| `runworker`            | Start local worker pool                             |
| `status <job_id>`      | Show result or error of a specific job              |
| `list tasks`           | List all discovered `@task` functions from manifest |
| `discover tasks` | Scan project recursively and discover tasks     |

---

## 🔍 Internals

### Task Auto-Discovery

* Recursive project scanning using `walker.py`
* `.nuvomignore` and glob-based filtering
* AST parsing of Python files to detect `@task` and `@task()` decorators without importing
* Static metadata extraction and task manifest caching

### Task Registry

* Thread-safe singleton `TaskRegistry` with duplicate task name detection
* Dynamic runtime registration via `@task` decorator
* Provides fast `get_task(name)` access for dispatching

### Task Decorator (`task.py`)

* Registers functions as Nuvom tasks with metadata: retries, timeout, lifecycle hooks
* Supports async job scheduling with `.delay()` and bulk `.map()`

### Worker Runtime

* Multi-threaded worker pool with batch job fetching for efficiency
* Graceful shutdown and retry logic
* Job lifecycle hooks execution

### Result Backends

* Pluggable interface (`BaseResultBackend`)
* Implemented: memory and file backends

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

## What’s New in v0.6?

- **Smart Worker Load Balancing:** Dynamic dispatching assigns jobs to the least busy worker, maximizing throughput and minimizing wait time.
- **Enhanced Task Metadata:** Tag and describe tasks directly in your code, then explore them with `nuvom list tasks`.
- **Developer Mode Auto-Reload:** Use `--dev` to auto-refresh your task registry on code or manifest changes—no need to restart workers.
- **Rich Logging & Error Display:** See colorful, structured logs and tracebacks that make debugging easier and faster.
- **Manifest Warm-Reload:** Manifest updates apply seamlessly during worker runtime.
- **Improved CLI Experience:** Manifest diffs, detailed task listings, and more—all powered by Rich.

---

## 🧪 Future (Backlog Ideas)

* [ ] Redis & SQLite queue backends
* [ ] DAG/task chaining support (like `job1.then(job2)`)
* [ ] Task versioning & signature validation
* [ ] Built-in dashboards & Prometheus metrics
* [ ] Distributed execution (multi-host worker mesh)
* [ ] Static `.nuvom_tasks.json` export for zero-import startup
* [ ] VSCode extension: visual queue monitor, task explorer

## 👨‍💻 Contributing

Nuvom continues to champion **simplicity, power, and developer happiness** in background task processing.
Want to help build Redis/SQLite backends or advanced scheduling? Contributions welcome! Open an issue or PR.

---

## 🪪 License

Apache License: Version 2.0, January 2004.
![license](http://www.apache.org/licenses/)

---
