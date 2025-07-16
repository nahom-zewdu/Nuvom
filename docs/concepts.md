# Core Concepts

Nuvom is built around a small number of powerful, composable concepts. Mastering these is key to using (and extending) the system effectively.

---

## 🧠 Task

A `Task` is a Python function decorated with `@task(...)`. It becomes a job template.

```python
@task(retries=2, timeout_secs=5)
def send_email(to, body):
    ...
````

Each task carries metadata like retry policy, timeout, and whether to store results.

---

## 🧱 Job

A `Job` is a serialized instance of a task + arguments.

```python
job = send_email.delay("alice@example.com", "hello")
```

Jobs are placed into a queue and executed by workers. You can inspect their metadata, result, status, and tracebacks.

---

## ⚙️ Worker

A **Worker** is a thread that pulls jobs from the queue and executes them.

Nuvom workers:

* Run in parallel (multi-threaded)
* Respect timeouts, retries, lifecycle hooks
* Use safe shutdown behavior (`SIGINT` triggers graceful stop)
* Work with plugin-registered backends

You can start a worker pool with:

```bash
nuvom runworker
```

---

## 🚦 Dispatcher

The **Dispatcher** handles the logic of turning a function call into a job.

* `.delay()` → single job
* `.map()` → batch of jobs
* Supports metadata injection
* Automatically selects queue backend from config

---

## 🪜 Queue Backend

A **Queue Backend** stores jobs awaiting execution.

Nuvom ships with:

* `MemoryJobQueue` – fast, ephemeral
* `FileJobQueue` – atomic, file-based persistence
* `SQLiteJobQueue` – relational queue with retries + visibility timeouts

Plugins can register custom queues. Each queue implements:

* `enqueue(job)`
* `dequeue(timeout)`
* `pop_batch(n)`
* `qsize()`
* `clear()`

---

## 📥 Result Backend

The **Result Backend** stores results or errors from executed jobs.

Built-in backends:

* `MemoryResultBackend` – ephemeral
* `FileResultBackend` – persistent JSON lines
* `SQLiteResultBackend` – full metadata, indexed queries

Backends must implement:

* `set_result(id, func, result)`
* `set_error(id, func, exc)`
* `get_result(id)`
* `get_error(id)`
* `get_full(id)`
* `list_jobs()`

---

## 🧾 Registry

The **Task Registry** is a thread-safe mapping of task names → callables.

* Populated at startup from `.nuvom/manifest.json`
* Also supports dynamic registration (`force`, `silent`, etc.)
* Used by workers to resolve jobs → functions

---

## 🔍 Task Discovery

Nuvom uses static analysis (AST) to find `@task` decorators in your codebase.

* No runtime imports required
* Supports `.nuvomignore` and folder filters
* Stores results in `.nuvom/manifest.json`
* Updated via `nuvom discover tasks`

This allows fast startup and avoids circular imports.

---

## 🔌 Plugins

Plugins extend Nuvom dynamically — they can register:

* Queue backends
* Result backends
* Monitoring hooks
* Lifecycle-aware systems

Plugins follow a standard `Plugin` protocol and are defined in `.nuvom_plugins.toml`.

```toml
[plugins]
queue_backend = ["my_module:MyQueuePlugin"]
```

Use `nuvom plugin test` to validate your plugin.

---

## 💡 Summary Table

| Concept      | Role                                       |
| ------------ | ------------------------------------------ |
| `@task`      | Defines metadata for background execution  |
| `Job`        | A task + args, queued for execution        |
| `Worker`     | Executes jobs from the queue               |
| `Queue`      | Stores jobs awaiting execution             |
| `Backend`    | Stores results, errors, and metadata       |
| `Dispatcher` | Converts function calls into jobs          |
| `Registry`   | Maps task names to functions               |
| `Discovery`  | Scans source code and builds task manifest |
| `Plugin`     | Dynamically extends Nuvom’s capabilities   |
