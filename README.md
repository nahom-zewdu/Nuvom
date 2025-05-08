# Nuvom — A Lightweight Python Task Queue (v0.2)

![status](https://img.shields.io/badge/version-v0.2-blue)
![python](https://img.shields.io/badge/python-3.8%2B-yellow)
![license](http://www.apache.org/licenses/)

**Nuvom** is a lightweight, developer-first task queue for Python with pluggable result backends, worker batching, CLI integration, and efficient job execution. Built with extensibility in mind, Nuvom is ideal for background task execution, prototypes, research tools, and embedded automation.

---

## 🔥 Features

- ✅ Background task registration with `.delay()`
- ✅ Built-in worker pool with graceful shutdown
- ✅ Configurable result backend: memory or file
- ✅ CLI commands for worker execution and job inspection
- ✅ Batch job fetching for worker efficiency
- ✅ Retry logic and automatic requeueing
- ✅ Minimal dependencies, no external services
- ✅ `.env`-based configuration

---

## 🚀 Getting Started

### 1. Install

```bash
pip install -e .
```

Nuvom has no runtime dependencies other than `rich`, `typer`, and `pydantic-settings`.

### 2. Define a Task

```python
# tasks.py
from nuvom.task import task

@task
def add(x, y):
    return x + y
```

### 3. Submit a Job

```python
# main.py
from tasks import add

job = add.delay(2, 3)
print(f"Job ID: {job.id}")
```

### 4. Start the Worker Pool

```bash
nuvom runworker
```

### 5. Check Job Status

```bash
nuvom status <job-id>
```

### ⚙️ Configuration

Nuvom loads settings from your `.env` file via `pydantic-settings`.

### 🔧 Sample .env

```env
NUVOM_ENVIRONMENT=dev
NUVOM_LOG_LEVEL=INFO
NUVOM_RESULT_BACKEND=file
NUVOM_MAX_WORKERS=4
NUVOM_BATCH_SIZE=1
NUVOM_JOB_TIMEOUT_SECS=60
NUVOM_QUEUE_MAXSIZE=0
```

### 📖 `NUVOM_RESULT_BACKEND` Options

| Value    | Description                               |
| -------- | ----------------------------------------- |
| `memory` | In-memory (non-persistent, fast)          |
| `file`   | File-based (`job_results/*.out`)          |
| `redis`  | [Planned] Persistent, production-grade   |
| `SQLite` | [Planned] Embedded persistent store       |

All backends must implement the interface defined in `BaseResultBackend`.

### 🧪 CLI Commands

```bash
nuvom --help
```

**Available commands:**

| Command          | Description                                    |
| ---------------- | ---------------------------------------------- |
| `config`         | Show current config loaded from `.env`         |
| `runworker`      | Start local worker pool                        |
| `status <job_id>` | Show the result or error of a specific job     |

### 🔍 Internals

#### `task.py`

- `@task` decorator registers any function as a Nuvom task
- Supports `.delay()` for async execution
- Internally serializes function, args, and metadata

#### `worker.py`

- Spawns worker threads
- Supports batch fetching from queue
- Automatically retries failed jobs if allowed
- Uses `set_result` / `set_error` for result backend

#### `result_backends/`

- `BaseResultBackend` defines pluggable interface
- Implemented: `MemoryResultBackend`, `FileResultBackend`
- Selected via `NUVOM_RESULT_BACKEND` config

#### `result_store.py`

- Central access point for result backends
- Uses singleton-style caching
- Abstracts storage away from workers or CLI

### 🧪 Testing

Basic integration testing is available by:

1. Submitting jobs in Python
2. Starting `nuvom runworker`
3. Polling `nuvom status <id>` to observe state transitions

Full test suite with mocks and assertions is planned for v0.3.

### 🗂 Roadmap

- ✅ **v0.1**
    Task definition and queue system
    Worker threading
    **v0.2**
    Pluggable result backends
    CLI enhancements
    File and memory result store
    Batch queue pulling

🔜 **v0.3 (Planned)**
    Redis backend
    SQLite backend
    Retry metadata tracking
    Job TTL & expiration
    Plugin support for custom backends
    Queue metrics and stats endpoint

### 👨‍💻 Contributing

Want to build a Redis or SQLite backend? Add advanced scheduling or tracing? Contributions welcome — open an issue or PR.

### 🪪 License

Apache License: Version 2.0, January 2004.
![license](http://www.apache.org/licenses/)
