# Quickstart

This guide walks you through installing Nuvom, defining your first task, and running workers — all in under 5 minutes.

---

## 🔧 Installation

Nuvom is under active development. Until the first stable release, install it from source:

```bash
git clone https://github.com/nahom-zewdu/Nuvom
cd Nuvom
pip install -e .
````

If you plan to contribute or run the documentation:

```bash
hatch shell
```

This will install all development and documentation dependencies inside a Hatch-managed environment.

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

## 3. Submit a Job

Dispatch jobs programmatically:

```python
from tasks import add

job = add.delay(5, 7)
print(job.id)
```

---

## 4. Run a Worker

Workers execute jobs in parallel threads:

```bash
nuvom runworker
```

You can configure worker behavior (e.g., count, batch size) via `.env`. See [Configuration](configuration.md) for full details.

---

## 5. Inspect Job Status

```bash
nuvom inspect job <job_id>
```

This shows result, error, traceback, retries remaining, and timestamps.

To view recent jobs:

```bash
nuvom history recent --limit 10
```

---

## 6. Retry Failed Jobs

Retry manually from Python:

```python
from nuvom.sdk import retry_job

retry_job("<job_id>")
```

CLI support for retrying is coming soon.

---
