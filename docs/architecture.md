# Nuvom Architecture

> **Clean, predictable, and pluggable built for developers who value control and clarity.**

Nuvom is a **plugin-first task engine** for Python. Its architecture cleanly separates task definition, discovery, queuing, execution, and result storage with each layer following a well-defined contract.

This makes it simple to start with zero external dependencies and equally simple to plug in Redis, PostgreSQL, or any custom backend as you scale.

---

## High-Level Overview

```text
     +-------------------------+
     |      @task decorator    |
     +-------------------------+
                  |
                  v
      +------------------------+
      |     Task Registry      | <--- loaded from manifest
      +------------------------+
                  |
                  v
+-------------+     +-------------------+
| Dispatcher  | --> |  Job Queue        |
+-------------+     +-------------------+
                         |
                         v
            +----------------------+ 
            |   Worker Pool        |
            | (Threads + Runner)   |
            +----------------------+ 
                         |
                         v
            +----------------------+ 
            |  Result Backend      |
            +----------------------+ 
```

---

## Core Components

### **Task API**

**Location:** `nuvom/task.py`

* The `@task` decorator registers a function as a Nuvom task.
* Metadata (like retries, timeouts, or result persistence) is attached at definition time.
* Exposes `.delay()`, `.map()`, and `.schedule()` for immediate, batched, or deferred execution.

---

### **Task Discovery**

**Location:** `nuvom/discovery/`

* AST-based discovery ensures safe, import-free scanning.
* Uses `.nuvomignore` to skip irrelevant paths.
* Caches output to `.nuvom/manifest.json` for near-instant worker startup.

Key modules:

* `walker.py` — file traversal
* `parser.py` — AST parsing
* `manifest.py` — manifest I/O
* `auto_register.py` — loads tasks into the registry

---

### **Task Registry**

**Location:** `nuvom/registry/registry.py`

* Thread-safe global registry.
* Prevents duplicate names unless `force=True`.
* Serves as the single source of truth for dispatchers and workers.

---

### **Dispatcher**

**Location:** `nuvom/dispatcher.py`

* Serializes and enqueues jobs via a consistent interface.
* Uses `msgpack` for efficient, portable serialization.
* Powers `.delay()` and `.map()` to create jobs programmatically.

---

### **Job Queues**

**Location:** `nuvom/queue_backends/`

Built-in backends:

* `MemoryJobQueue`
* `FileJobQueue`
* `SQLiteJobQueue`

Custom queues follow a simple interface:

```python
enqueue(job)
dequeue(timeout=None)
pop_batch(batch_size)
qsize()
clear()
```

---

### **Workers & Execution**

**Location:** `nuvom/worker.py`, `nuvom/execution/job_runner.py`

* Multi-threaded worker pool with controlled concurrency.
* Executes jobs with:

  * Timeouts
  * Retries
  * Lifecycle hooks (`before_job`, `after_job`, `on_error`)
* Graceful shutdown with log flushing and clean teardown.

---

### **Result Backends**

**Location:** `nuvom/result_backends/`

Built-in options:

* `MemoryResultBackend`
* `FileResultBackend`
* `SQLiteResultBackend`

All result backends implement:

```python
set_result(job_id, ...)
get_result(job_id)
set_error(job_id, ...)
get_error(job_id)
get_full(job_id)
list_jobs()
```

Custom result backends can be registered via `.nuvom_plugins.toml`.

---

### **Logging**

**Location:** `nuvom/log.py`

* Unified, developer-friendly logging built on `Rich`.
* Color-coded, exception-aware output for clean debugging and CLI visibility.

---

## Plugin Architecture

**Location:** `nuvom/plugins/`

* Extend queues, result backends, or monitoring exporters.
* Lifecycle hooks: `start()` and `stop()` for controlled resource management.

Example `.nuvom_plugins.toml`:

```toml
[plugins]
queue_backend = ["custom.module:MyQueue"]
result_backend = ["custom.module:MyResult"]
```

---

## Job Lifecycle

1. Developer defines a task with `@task`.
2. `nuvom discover tasks` scans and caches it in the manifest.
3. A job is queued using `.delay()`, `.map()`, or `.schedule()`.
4. Worker dequeues the job.
5. `JobRunner`:

   * Fires lifecycle hooks
   * Executes the task with retry and timeout logic
   * Stores result or error in the backend
6. Result metadata can be queried via CLI or SDK.

---

## Design Principles

* **Clean separation** — each layer has a single responsibility
* **Pluggable by design** — backends, metrics, and hooks are swappable
* **Predictable behavior** — no hidden daemons or background processes
* **Cross-platform consistency** — works the same on Linux, macOS, and Windows
* **Readable source** — easy to debug, easy to extend

---

For more details:

* [Contributing](./contributing.md)
* [Roadmap](./roadmap.md)
* [README](../README.md)

---
