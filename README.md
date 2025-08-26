# nuvom

> Nuvom gives developers a task engine they can trust: clean APIs, zero magic, and predictable behavior from local dev to production scale.

![status](https://img.shields.io/badge/version-v0.11-blue)
![python](https://img.shields.io/badge/python-3.8%2B-yellow)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

---

## Why Nuvom?

**Nuvom** is a modern task engine for Python that focuses on **clarity, reliability, and flexibility**.
It’s simple to start, easy to scale, and built for developers who value predictable, production-ready behavior.

### Core Principles

* **Developer-first design** — clean APIs, no magic, no surprises
* **Pluggable architecture** — use SQLite, PostgreSQL, Redis, or your own backend
* **Cross-platform** — consistent behavior on Linux, macOS, and Windows
* **Static task discovery** — AST-powered for speed and safety
* **Built-in scheduling** — one-off, interval, or cron-style recurring jobs
* **Predictable in production** — fault-tolerant workers and durable job persistence

---

## Installation

```bash
pip install nuvom
```

---

## Quickstart

### 1. Define a Task

```python
from nuvom.task import task

@task(retries=2, retry_delay_secs=5, timeout_secs=3, store_result=True)
def add(x, y):
    return x + y
```

### 2. Discover Tasks

```bash
nuvom discover tasks
```

Generates `.nuvom/manifest.json` for faster worker startup.

### 3. Queue a Job

```python
from tasks import add

job = add.delay(5, 7)
print(job.id)
```

### 4. Schedule a Job

```python
from datetime import timedelta, datetime, timezone
from tasks import add

# Run at a specific time (2038 iykyk)
add.schedule(5, 7, at=datetime(2038, 1, 19, 3, 14, 7, tzinfo=timezone.utc)) 

# Run after 30 seconds
add.schedule(5, 7, in_=timedelta(seconds=30))

# Repeat every 5 minutes
add.schedule(2, 3, interval=300)

# Daily at midnight UTC
add.schedule(1, 2, cron="0 0 * * *")
```

Start the scheduler service:

```bash
nuvom runscheduler
```

Workers will automatically pick up due jobs.

### 5. Run the Worker

```bash
nuvom runworker
```

### 6. Inspect Results

```bash
nuvom inspect job <job_id>
```

---

## Plugin Architecture

Nuvom is modular by design:

* Implement custom queue or result backends
* Extend scheduling with custom triggers
* Add metrics, persistence, or monitoring plugins

Configure via `.nuvom_plugins.toml`.

---

## Documentation

Explore:

* Advanced task & scheduling options
* Plugin development guides
* CLI usage and environment setup
* Architecture and internals

👉 **[Documentation](https://nuvom.netlify.app)**

---

## License

Apache 2.0 - open, reliable, and production-ready.
