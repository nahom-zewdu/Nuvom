# Nuvom

> 🧠 Lightweight, plugin-first task queue for Python — no Redis, no brokers, fully Windows-compatible.

Nuvom is a developer-first background task execution engine that helps you **queue**, **execute**, and **persist** background jobs — without the baggage of Celery or infrastructure-heavy dependencies.

Built with clarity, speed, and extensibility in mind, Nuvom is:

- 🪟 **Fully Windows-compatible** — no POSIX-only dependencies
- 🔌 **Plugin-first** — extend queues, backends, and metrics with ease
- ⚙️ **No Redis, no RabbitMQ, no Docker** — just Python
- 🧠 **AST-powered static discovery** — no import-time magic
- 🚀 **CLI-first DX** — introspect jobs, retry failures, inspect task metadata
- 📦 **Manifest caching** — blazing-fast task resolution for workers and tooling

---

## Why Nuvom?

Traditional tools like Celery and RQ assume:

- Linux environments
- Redis or RabbitMQ brokers
- Complex operational setups

Nuvom throws those assumptions out the window. It's designed for:

- **Solo developers or small teams** who want productivity without infra.
- **Plugin authors** who need pluggable, testable task systems.
- **Cross-platform developers** (especially on Windows).
- **Performance-focused workflows** with static analysis, manifest caching, and real observability.

---

## Key Features

✅ `@task` decorator with `.delay()` / `.map()`  
✅ AST-based static discovery — no imports  
✅ Graceful retry + timeout logic  
✅ Pluggable result and queue backends  
✅ SQLite, file, and in-memory backends built-in  
✅ Plugin loader with `.toml` registry  
✅ Prometheus metrics plugin  
✅ Job metadata, tracebacks, and historical CLI inspection  
✅ Typed config via `.env` + Pydantic  
✅ CLI commands to run, retry, inspect, and monitor jobs  
✅ Compatible with Python 3.8+

---

## Example

```python
from nuvom.task import task

@task(retries=2, retry_delay_secs=5, timeout_secs=3)
def add(x, y):
    return x + y

# Submit job
job = add.delay(2, 3)
````

```bash
nuvom runworker                # Start workers
nuvom inspect job <job_id>    # Inspect job result and metadata
```

---

## Installation

```bash
git clone https://github.com/nahom-zewdu/Nuvom
cd Nuvom
pip install -e .
```

---

## What’s Next?

- [Quickstart →](quickstart.md)
- [Configuration →](configuration.md)
- [CLI →](cli.md)
- [Core Concepts →](concepts.md)
- [Plugin System →](plugins.md)
- [Architecture →](architecture.md)
- [Roadmap →](roadmap.md)
- [Contributing →](contributing.md)
- [FAQ →](faq.md)

---

## License

Apache 2.0 — use it freely, build responsibly.
