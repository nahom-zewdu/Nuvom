# `nuvom`

> Lightweight, plugin-first task queue for Python. No Redis, Windows-native, AST-powered task discovery, and extensible by design.

![status](https://img.shields.io/badge/version-v0.10-blue)
![python](https://img.shields.io/badge/python-3.8%2B-yellow)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

---

## Why Nuvom?

**Nuvom** is a developer-first job execution engine that helps you queue, run, and persist background tasks — without requiring Redis, Celery, or any infrastructure.

### Core Principles

- **Windows-native** — built for cross-platform reliability
- **Plugin-first** — customize queue engines, backends, discovery logic
- **No brokers** — zero dependency setup
- **Static task discovery** — powered by AST, not imports
- **Manifest caching** — ultra-fast CLI startup

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

### 2. Queue a Job

```python
from tasks import add

job = add.delay(5, 7)
print(job.id)
```

### 3. Run the Worker

```bash
nuvom runworker
```

### 4. Inspect the Result

```bash
nuvom inspect job <job_id>
```

---

## Plugin Architecture

Nuvom is extensible by design. You can:

- Implement custom queue engines
- Hook in your own result backends
- Add Prometheus metrics or distributed storage
- Auto-discover tasks with custom logic

Everything is modular and pluggable via a `.nuvom_plugins.toml` file.

---

## Full Documentation

Head over to the official documentation site for:

- Advanced task options
- Plugin development guides
- Architecture & internal design
- CLI usage and environment setup

👉 **[https://nuvom.netlify.app](https://nuvom.netlify.app)**

---

## License

Apache 2.0 — use it freely, build responsibly.
