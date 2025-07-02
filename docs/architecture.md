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

Use `Plugin` protocol to add dynamic queue backends that load at worker startup.

---

### ✅ Workers & Execution

Location: `nuvom/worker.py`, `nuvom/execution/job_runner.py`

- `Worker`: runs in its own thread, polls the queue for jobs.
- `JobRunner`: handles timeout, retries, and lifecycle hooks (`before_job`, `after_job`, `on_error`).
- Jobs are executed in isolated `ThreadPoolExecutor`s.
- Results or errors are stored after execution.
- **Graceful shutdown lifecycle**: When a shutdown is triggered, workers:

  - Stop accepting new jobs
  - Finish current job in-flight
  - Log safe shutdown and exit cleanly

---

### ✅ Result Backends

Location: `nuvom/result_backends/`

Backends:

- `MemoryResultBackend`: in-memory result store.
- `FileResultBackend`: persistent, file-based result storage.
- `SQLiteResultBackend`: fast, file-based relational backend (v0.9+).
- 🔌 Plugin-aware: load external result backends via `.nuvom_plugins.toml`.

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
- `sqlite_db_path` config for SQLite backend (v0.9+).
- `nuvom/utils/`: Filesystem helpers like `safe_remove`, `.nuvomignore` parsing.
- `nuvom/serialize/`: Msgpack-based (or custom) serialization support.
- `nuvom/plugins/`: 🆕 Plugin system logic (v0.9+)

  - `loader.py`: Parses `.nuvom_plugins.toml`, loads user plugins dynamically
  - `registry.py`: Central plugin registry for queue/result backend types
  - `types.py`: `Plugin` protocol every plugin must follow

---

## 🔌 Plugin Architecture

You can easily extend Nuvom by:

- Adding a new queue backend: subclass `BaseJobQueue`
- Adding a result backend: subclass `BaseResultBackend`
- Creating your own CLI commands via Typer (see `nuvom/cli/`)
- Hooking into the manifest or discovery system
- Using dynamic imports and lazy task loading

**v0.9 Plugin System Details**:

- Plugin entrypoints defined in `.nuvom_plugins.toml`
- Each plugin must implement the `Plugin` protocol (`name`, `type`, `load()` method)
- Registered on worker startup, not CLI runtime
- CLI commands:

  - `nuvom plugin list`
  - `nuvom plugin inspect <name>`
  - `nuvom plugin test`

Example plugin definition:

```toml
[plugins]
queue_backend = ["my_backend.queue:CustomQueue"]
result_backend = ["my_backend.result:CustomResult"]
```

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

7. If shutdown is triggered:

   - Worker stops polling new jobs
   - Gracefully completes current execution
   - Logs shutdown event

8. `nuvom inspect job <job_id>` shows detailed metadata for executed jobs.
9. `nuvom history recent` with `--limit` and `--status` flag shows list of jobs with their metadata.

---

## 🧠 Design Philosophy

- ✅ Prefer clarity and simplicity over premature optimization.
- ✅ No Redis, Celery, or RabbitMQ required.
- ✅ Treat all components as replaceable and pluggable.
- ✅ Developer-first: CLI-first, Windows support, minimal deps.
- ✅ Codebase designed for learning, contribution, and extension.

---

## 🛣️ Road Ahead

What's next (v1.0 and beyond):

- [x] Plugin loader and dynamic backend system ✅ *(v0.9)*
- [x] SQLite result backend ✅ *(v0.9)*
- [x] Graceful shutdown logic ✅ *(v0.9)*
- [ ] Redis-based queue and result backends
- [ ] DAG-style task chaining
- [ ] Distributed multi-host execution
- [ ] Rich visual dashboard
- [ ] VSCode extension

---

For more details, see the [`README`](../README.md) and [`CONTRIBUTING`](../CONTRIBUTING.md).
