# Core Concepts

Nuvom is built around a small number of powerful, composable concepts. Mastering these is key to using (and extending) the system effectively, now including built-in scheduling.

---

## Task

A `Task` is a Python function decorated with `@task(...)`. It becomes a job template.

```python
@task(retries=2, timeout_secs=5)
def send_email(to, body):
    ...
```

Each task carries metadata like retry policy, timeout, whether to store results, and scheduling configuration.

---

## Job

A `Job` is a serialized instance of a task + arguments.

```python
job = send_email.delay("alice@example.com", "hello")
```

Jobs are queued and executed by workers. You can inspect metadata, results, status, and tracebacks.

---

## Worker

A **Worker** pulls jobs from the queue and executes them.

Nuvom workers:

* Run in parallel (multi-threaded)
* Respect timeouts, retries, and lifecycle hooks
* Use safe shutdown behavior (`SIGINT` triggers graceful stop)
* Work with plugin-registered backends
* Execute scheduled jobs seamlessly, respecting intervals, cron expressions, and one-off timings

Start a worker pool with:

```bash
nuvom runworker
```

---

## Dispatcher

The **Dispatcher** converts function calls into jobs.

* `.delay()` → single job
* `.map()` → batch jobs
* `.schedule()` → schedule jobs (one-off, interval, or cron)
* Supports metadata injection
* Automatically selects queue backend from config

---

## Queue Backend

A **Queue Backend** stores jobs awaiting execution.

Built-in:

* `MemoryJobQueue` – fast, ephemeral
* `FileJobQueue` – atomic, file-based persistence
* `SQLiteJobQueue` – relational queue with retries + visibility timeouts

Custom backends can be added via plugins. Each queue implements:

* `enqueue(job)`
* `dequeue(timeout)`
* `pop_batch(n)`
* `qsize()`
* `clear()`

---

## Result Backend

Stores results or errors from executed jobs.

Built-in:

* `MemoryResultBackend`
* `FileResultBackend`
* `SQLiteResultBackend`

Backends implement:

* `set_result(id, func, result)`
* `set_error(id, func, exc)`
* `get_result(id)`
* `get_error(id)`
* `get_full(id)`
* `list_jobs()`

---

## Registry

The **Task Registry** maps task names → callables.

* Populated from `.nuvom/manifest.json`
* Supports dynamic registration (`force`, `silent`)
* Used by workers to resolve jobs → functions

---

## Task Discovery

Uses AST parsing to find `@task` decorators.

* No runtime imports
* Supports `.nuvomignore`
* Results cached in `.nuvom/manifest.json`
* Updated via `nuvom discover tasks`

Enables fast startup and avoids circular imports.

---

## Scheduling

Scheduling is built into Nuvom tasks:

* **One-off**: run once at a specific time
* **Interval**: run repeatedly at fixed intervals
* **Cron**: run with cron expressions

Example:

```python
from datetime import timedelta, datetime, timezone

# Run once at a specific time
send_email.schedule("alice@example.com", "hello", at=datetime(2025,8,25,12,0,tzinfo=timezone.utc))

# Run once after 30 seconds
send_email.schedule("alice@example.com", "hello", in_=timedelta(seconds=30))

# Run every 5 minutes
send_email.schedule("alice@example.com", "hello", interval=300)

# Cron-style: daily at midnight UTC
send_email.schedule("alice@example.com", "hello", cron="0 0 * * *")
```

Scheduled jobs integrate seamlessly with workers, retries, and plugins.

---

## Plugins

Extend Nuvom dynamically:

* Queue backends
* Result backends
* Monitoring hooks
* Lifecycle-aware systems

Defined in `.nuvom_plugins.toml` and validated with `nuvom plugin test`.

---

## Summary Table

| Concept      | Role                                       |
| ------------ | ------------------------------------------ |
| `@task`      | Defines metadata for background execution, including scheduling |
| `Job`        | A task + args, queued for execution        |
| `Worker`     | Executes jobs from the queue, including scheduled jobs |
| `Queue`      | Stores jobs awaiting execution             |
| `Backend`    | Stores results, errors, and metadata       |
| `Dispatcher` | Converts function calls into jobs, supports `.delay()`, `.map()`, `.schedule()` |
| `Registry`   | Maps task names to functions               |
| `Discovery`  | Scans source code and builds task manifest |
| `Plugin`     | Dynamically extends Nuvom’s capabilities   |
| `Scheduler`  | Manages one-off, interval, and cron jobs across workers |
