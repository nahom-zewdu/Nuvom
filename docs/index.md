# Nuvom

> **Nuvom gives developers a task engine they can trust clean APIs, zero magic, and predictable behavior from local dev to production scale.**

Nuvom is a **developer-first background task engine** for Python. It lets you **queue, schedule, and persist** background jobs with predictable behavior without depending on heavyweight infrastructure.

When you need more power, Nuvom’s **pluggable backend architecture** lets you integrate with **SQLite, PostgreSQL, Redis, RabbitMQ**, or your own backend for advanced workflows and scaling.

---

## Why Nuvom?

Nuvom is built for developers who want a **clear, reliable, and flexible** task system that scales with their needs — from a single-machine project to production-grade deployments.

It’s designed for:

* **Developers and teams** who want simplicity without giving up control
* **Plugin authors** who need a modular, testable task engine
* **Cross-platform environments** — consistent behavior on Linux, macOS, and Windows
* **Predictable production workflows** with static discovery, manifest caching, and clean observability
* **Advanced setups** that need pluggable backends for durability and scale

---

## Key Features

* **Clean task API** with `@task`, `.delay()`, `.map()`, and `.schedule()`
* **Pluggable architecture** — SQLite, Postgres, Redis, RabbitMQ, or custom backends
* **Static task discovery** — AST-powered, no runtime imports needed
* **Multiple scheduling modes** — one-off (`at` / `in_`), interval, cron
* **Durable job execution** — retries, timeouts, and predictable failure handling
* **Plugin loader** with `.toml` registry for easy extension
* **Observability built-in** — job metadata, tracebacks, and optional Prometheus metrics
* **Typed configuration** via `.env` and Pydantic
* **Cross-platform** — Python 3.8+ on Linux, macOS, and Windows

---

## Example: Scheduling a Task

```python
from datetime import timedelta
from nuvom.task import task

@task(retries=2, retry_delay_secs=5, timeout_secs=3)
def send_reminder(user_id):
    print(f"Reminder sent to user {user_id}")

# Run once in 5 minutes
send_reminder.schedule(123, in_=timedelta(minutes=5))

# Run every hour
send_reminder.schedule(123, interval=3600)

# Cron-style: every Monday at 9am UTC
send_reminder.schedule(123, cron="0 9 * * MON")
```

---

## What’s Next?

* [Quickstart →](quickstart.md)
* [Configuration →](configuration.md)
* [CLI →](cli.md)
* [Core Concepts →](concepts.md)
* [Scheduler →](scheduler.md)
* [Plugin System →](plugins.md)
* [Architecture →](architecture.md)
* [Roadmap →](roadmap.md)
* [Contributing →](contributing.md)
* [FAQ →](faq.md)

---

## License

Apache 2.0 - open, reliable, and production-ready.
