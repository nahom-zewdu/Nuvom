# 🧠 Nuvom Architecture

This document describes the internal architecture of the **Nuvom** task execution engine — covering the major modules, design decisions, and how they fit together.

---

## 🧩 High-Level Overview

Nuvom is built around the idea of decoupling **task definition**, **discovery**, **execution**, **queuing**, and **result storage**. Each component is pluggable and adheres to a clear contract via abstract base classes.

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

## 🧱 Core Components

### ✅ `@task` Decorator

Location: `nuvom/task.py`

- Wraps a function to mark it as a Nuvom task.
- Adds metadata (retries, timeouts, lifecycle hooks).
- Registers the task into the in-memory registry.
- Supports `.delay()` and `.map()` for dispatching jobs.

---

### ✅ Task Discovery

Location: `nuvom/discovery/`

- Uses AST parsing to find functions decorated with `@task`.
- Works without importing modules (safe for large codebases).
- `walker.py`: recursively traverses the file tree.
- `parser.py`: parses Python files and identifies task definitions.
- `.nuvomignore`: used to skip files/directories.
- `manifest.py`: stores a cache of discovered tasks with hash metadata.
- `auto_register.py`: loads discovered tasks into the registry.

---

### ✅ Task Registry

Location: `nuvom/registry/registry.py`

- Thread-safe singleton (`TaskRegistry`) that holds all registered tasks.
- Prevents duplicate task names unless `force=True`.
- Used at runtime to resolve task names to function references.

---

### ✅ Dispatcher

Location: `nuvom/dispatcher.py` *(coming in v0.7, currently part of CLI and task methods)*

- Enqueues jobs into the selected job queue.
- Serializes jobs into a portable format (`msgpack`).
- Provides methods like `.delay()` or bulk `.map()`.

---

### ✅ Job Queues

Location: `nuvom/queue_backends/`

Backends:

- `MemoryJobQueue`: simple thread-safe in-memory queue.
- `FileJobQueue`: atomic file-based queue with `.msgpack` serialization.

All queues must implement:

- `enqueue(job)`
- `dequeue(timeout)`
- `pop_batch(batch_size)`
- `qsize()`
- `clear()`

Custom queues can be added by implementing `BaseJobQueue`.

---

### ✅ Workers & Execution

Location: `nuvom/worker.py`, `nuvom/execution/job_runner.py`

- `Worker`: runs in its own thread, polls the queue for jobs.
- `JobRunner`: handles timeout, retries, and lifecycle hooks (`before_job`, `after_job`, `on_error`).
- Jobs are executed in isolated `ThreadPoolExecutor`s.
- Results or errors are stored after execution.

---

### ✅ Result Backends

Location: `nuvom/result_backends/`

Backends:

- `MemoryResultBackend`: in-memory result store.
- `FileResultBackend`: persistent, file-based result storage.

All backends implement:

- `set_result(job_id, func_name result)`
- `get_result(job_id)`
- `set_error(job_id, func_name, error)`
- `get_error(job_id)`
- `get_full(job_id)`
- `list_jobs()`

---

### ✅ Logging

Location: `nuvom/log.py`

- Centralized logging via `RichHandler`.
- Uses markup, colorized tracebacks, and disabled noisy paths.
- All modules use `logger = get_logger()` for consistent output.

---

## 🧰 Utility Modules

- `nuvom/config.py`: Loads environment variables via `pydantic-settings`.
- `nuvom/utils/`: Filesystem helpers like `safe_remove`, `.nuvomignore` parsing.
- `nuvom/serialize/`: Msgpack-based (or custom) serialization support.

---

## 🔌 Plugin Architecture

You can easily extend Nuvom by:

- Adding a new queue backend: subclass `BaseJobQueue`
- Adding a result backend: subclass `BaseResultBackend`
- Creating your own CLI commands via Typer (see `nuvom/cli/`)
- Hooking into the manifest or discovery system
- Using dynamic imports and lazy task loading

---

## ♻️ Lifecycle of a Job

1. Developer defines a task with `@task`.
2. `nuvom discover tasks` finds and caches the task metadata.
3. `nuvom runworker` starts worker pool and loads registry.
4. A job is submitted via `.delay()` and stored in the queue.
5. Worker dequeues job and passes it to `JobRunner`.
6. `JobRunner`:
   - Marks job running
   - Calls `before_job()`
   - Runs the task
   - Calls `after_job()` or `on_error()`
   - Stores result or error
   - Retries if needed

7. `nuvom inspect job <job_id>` shows detailed metadata for executed jobs.
8. `nuvom history recent` with `--limit` and `--status` flag shows list of jobs with their metadata.

---

## 🧠 Design Philosophy

- ✅ Prefer clarity and simplicity over premature optimization.
- ✅ No Redis, Celery, or RabbitMQ required.
- ✅ Treat all components as replaceable and pluggable.
- ✅ Developer-first: CLI-first, Windows support, minimal deps.
- ✅ Codebase designed for learning, contribution, and extension.

---

## 🛣️ Road Ahead

Coming soon:

- Redis and SQLite queue/result backends
- DAG-style task chaining
- Plugin registry system
- Multi-host distributed workers

---

For more details, see the [`README`](../README.md) and [`CONTRIBUTING`](../CONTRIBUTING.md).
