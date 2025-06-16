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

## 🗂 Roadmap

✅ **v0.1**

* Basic task queue with threading and simple worker

✅ **v0.2**

* Result backends and CLI improvements

✅ **v0.3**

* Pluggable queue backends and improved persistence

✅ **v0.4**

* Batch-aware execution engine with lifecycle hooks

✅ **v0.5**

* Recursive, AST-powered task auto-discovery with manifest caching
* Thread-safe registry and enhanced task decorator API
* Rich CLI commands for task listing and manifest management

🛠 **v0.6 Goal**

* Runtime execution refactor for scalability and debugging mode
* Job tracing and enhanced error handling
* Support for distributed execution and monitoring

---

## 👨‍💻 Contributing

Want to help build Redis/SQLite backends or advanced scheduling? Contributions welcome! Open an issue or PR.

---

## 🪪 License

Apache License: Version 2.0, January 2004.
![license](http://www.apache.org/licenses/)

---
