# Quickstart

This guide walks you through setting up Nuvom, defining your first task, and running workers — all in under 5 minutes.

---

## 🔧 Installation

Nuvom is under active development. Until the first stable release (v1.0), install it from source:

```bash
git clone https://github.com/nahom-zewdu/Nuvom
cd Nuvom
pip install -e .
````

You’ll also want dev dependencies if you plan to contribute:

```bash
pip install -r requirements-dev.txt
```

---

## 1. Define a Task

Tasks are regular Python functions decorated with `@task`.

```python
# tasks.py
from nuvom.task import task

@task(retries=2, retry_delay_secs=5, timeout_secs=3, store_result=True)
def add(x, y):
    return x + y
```

The decorator adds metadata (timeouts, retries) and enables `.delay()` and `.map()` dispatching.

---

## 2. Discover Tasks (Optional but Recommended)

Nuvom uses AST-based static discovery to scan your codebase and build a manifest of available tasks.

Run this once:

```bash
nuvom discover tasks
```

This generates `.nuvom/manifest.json` which speeds up worker startup and avoids runtime imports.

---

## 3. Submit a Job

In your Python code:

```python
from tasks import add

job = add.delay(5, 7)
print(job.id)
```

The `.delay()` method serializes the function call and queues it as a job.

---

## 4. Run a Worker

Workers execute jobs in parallel threads. Start the worker pool with:

```bash
nuvom runworker
```

You can configure worker count, batch size, and more via `.env`. See [Configuration](configuration.md) for full details.

---

## 5. Inspect Job Status

```bash
nuvom inspect job <job_id>
```

This shows metadata, result or error, traceback, retries left, and more.

To view recent jobs:

```bash
nuvom history recent --limit 10
```

---

## 6. Retry Failed Jobs (Manually)

```python
from nuvom.sdk import retry_job

retry_job("<job_id>")
```

This requeues a failed job manually from code. You can also retry via the CLI (coming soon).

---
