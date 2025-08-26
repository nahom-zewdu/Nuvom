# Quickstart

This guide walks you through installing Nuvom, defining your first task, scheduling it, and running workers all in under 5 minutes.

---

## Installation

```bash
pip install nuvom
```

---

## 1. Define a Task

Tasks are regular Python functions decorated with `@task`:

```python
# tasks.py
from nuvom.task import task

@task(retries=2, retry_delay_secs=5, timeout_secs=3, store_result=True)
def add(x, y):
    return x + y
```

The decorator enables retry logic, timeouts, and lets you dispatch with `.delay()` or `.map()`.

---

## 2. Discover Tasks (Optional but Recommended)

Nuvom uses static AST-based discovery to find task definitions without executing your code.

Run once:

```bash
nuvom discover tasks
```

This generates `.nuvom/manifest.json` to speed up worker startup and avoid runtime imports.

---

## 3. Submit a Job Immediately

Dispatch jobs programmatically:

```python
from tasks import add

job = add.delay(5, 7)
print(job.id)
```

---

## 4. Schedule a Task

Tasks expose `.schedule()` for deferred or recurring execution. Scheduling works seamlessly across workers and backends.

```python
from datetime import timedelta, datetime, timezone
from tasks import add

# Run at a specific time (2038 iykyk)
add.schedule(5, 7, at=datetime(2038, 1, 19, 3, 14, 7, tzinfo=timezone.utc)) 

# Run once after 30 seconds
add.schedule(5, 7, in_=timedelta(seconds=30))

# Run every 5 minutes (interval scheduling)
add.schedule(2, 3, interval=300)

# Cron-style: every day at midnight UTC
add.schedule(1, 2, cron="0 0 * * *")
```

Start the scheduler service:

```bash
nuvom runscheduler
```

Workers will automatically execute due jobs.

---

## 5. Run a Worker

Workers execute jobs in parallel threads:

```bash
nuvom runworker
```

You can configure worker behavior (count, batch size, scheduler backend, etc.) via `.env`. See [Configuration](configuration.md) for details.

---

## 6. Inspect Job Status

```bash
nuvom inspect job <job_id>
```

This shows result, error, traceback, retries remaining, and timestamps.

To view recent jobs:

```bash
nuvom history recent --limit 10
```

---

## 7. Retry Failed Jobs

Retry manually from Python:

```python
from nuvom.sdk import retry_job

retry_job("<job_id>")
```

CLI support for retrying is available in the next release.

---
