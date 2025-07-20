# Nuvom Architecture

This document explains the internal architecture of **Nuvom**, a lightweight, plugin-first task execution engine for Python.

---

## High-Level Overview

Nuvom is designed to **decouple** task definition, discovery, execution, queuing, and result storage. Each layer is pluggable and follows a clearly defined contract via abstract base classes.

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

### `@task` Decorator

**Location:** `nuvom/task.py`

* Wraps a function to register it as a Nuvom task.
* Adds metadata (`retries`, `timeout_secs`, etc.).
* Supports `.delay()` and `.map()` for job dispatch.
* All tasks are auto-registered via AST and manifest system.

---

### Task Discovery

**Location:** `nuvom/discovery/`

* Uses AST parsing (not imports) to detect decorated `@task` functions.
* Avoids side-effects, safe for large codebases.
* Uses `.nuvomignore` to skip paths.
* Output is cached in `.nuvom/manifest.json` for fast reloading.

Key files:

* `walker.py` – file traversal
* `parser.py` – AST parsing
* `manifest.py` – manifest file I/O
* `auto_register.py` – registry loader

---

### Task Registry

**Location:** `nuvom/registry/registry.py`

* Thread-safe global registry for tasks.
* Validates task names (prevents duplicates unless `force=True`).
* Used by the dispatcher and job runner to resolve function names.

---

### Dispatcher

**Location:** `nuvom/dispatcher.py`

* Orchestrates job submission: serializes, enqueues, retries.
* Provides `.delay()`, `.map()`, and job creation utilities.
* Uses `msgpack` for efficient, cross-platform job serialization.

---

### Job Queues

**Location:** `nuvom/queue_backends/`

Built-in backends:

* `MemoryJobQueue`
* `FileJobQueue`
* `SQLiteJobQueue` (v0.10)

Required interface methods:

```python
enqueue(job)
dequeue(timeout=None)
pop_batch(batch_size)
qsize()
clear()
```

Custom backends can be added via the plugin system.

---

### Workers & Job Execution

**Location:** `nuvom/worker.py`, `nuvom/execution/job_runner.py`

* Each worker runs in its own thread.
* Jobs are executed with timeouts, retries, and lifecycle hooks:

  * `before_job()`
  * `after_job()`
  * `on_error()`
* ThreadPoolExecutor is used internally for concurrency.
* Supports graceful shutdown with log flushing and safe teardown.

---

### Result Backends

**Location:** `nuvom/result_backends/`

Built-in backends:

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

Use `.nuvom_plugins.toml` to register custom plugins.

---

### Logging

**Location:** `nuvom/log.py`

* Unified logging across all modules using Rich.
* Logs are styled, color-coded, and exception-aware.
* Categories: `debug`, `info`, `warning`, `error`.

---

## Plugin Architecture

**Location:** `nuvom/plugins/`

Nuvom supports plugins for:

* Queues
* Result backends
* Monitoring/exporters

Plugins follow a strict `Plugin` protocol with `start()` and `stop()` lifecycle methods.

```toml
[plugins]
queue_backend = ["custom.module:MyQueue"]
result_backend = ["custom.module:MyResult"]
```

Each plugin must register itself via a `Plugin` subclass, and may use `register_queue_backend()` or `register_result_backend()`.

---

## Job Lifecycle

1. Developer defines a task with `@task`.
2. `nuvom discover tasks` parses and caches it.
3. Job is queued with `.delay()` or `.map()`.
4. Worker dequeues the job.
5. `JobRunner`:

   * Triggers lifecycle hooks
   * Executes task with timeout/retry logic
   * Stores result or error
6. Job metadata is saved in the selected result backend.
7. Results are queried via SDK or CLI.

---

## Design Principles

* Plugin-first, interface-driven
* No global daemons or dependencies like Redis
* Developer-first: minimal config, rich logging, CLI tooling
* Native on Windows, Linux, macOS
* Built to teach: readable source, clean separation

---

For more, see:

* [CONTRIBUTING](./contributing.md)
* [README](../README.md)
* [Roadmap](./roadmap.md)
