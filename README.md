# `nuvom`

> 🧠 Lightweight, plugin-first task queue for Python. No Redis, Windows-native, AST-powered task discovery, and extensible by design.

![status](https://img.shields.io/badge/version-v0.10-blue)
![python](https://img.shields.io/badge/python-3.8%2B-yellow)
![license](https://img.shields.io/badge/license-Apache--2.0-green)

---

## ✨ Why Nuvom?

Nuvom is a developer-first job execution engine that helps you queue, execute, and persist background tasks—without needing Redis, Celery, or any infrastructure.

Key philosophies:

- 🪟 **Windows-native** (no Linux-only assumptions)
- 🔌 **Plugin-first**: easily extend queues, backends, and task loaders
- ⚙️ **No Redis**, **no brokers**, and **no external services**
- 📜 **Static task discovery** via AST parsing — zero import side-effects
- ⚡ **Manifest caching** for fast CLI performance

---

## 📖 Documentation

Full guides and reference material are available in the [`docs/`](./docs) directory:

- [Quickstart](docs/quickstart.md)
- [CLI Reference](docs/cli.md)
- [Core Concepts](docs/concepts.md)
- [Architecture Overview](docs/architecture.md)
- [Plugin System](docs/plugins.md)
- [Configuration](docs/configuration.md)
- [Roadmap & Milestones](docs/roadmap.md)
- [FAQ](docs/faq.md)

---

## 📦 Installation

```bash
pip install nuvom
```

---

## ⚙️ Quickstart

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

### 4. Inspect Job Result

```bash
nuvom inspect job <job_id>
```

---

## 🧪 CLI Overview

Nuvom provides a rich CLI for listing tasks, inspecting job metadata, retrying failures, and managing plugins.

```bash
nuvom --help
```

Full command list: [CLI Reference](docs/cli.md)

---

## 🔧 Configuration

Nuvom uses `.env`-based configuration powered by `pydantic-settings`.
Full details: [Configuration Guide](docs/configuration.md)

---

## 📊 Monitoring

Nuvom includes a Prometheus plugin that exposes live metrics (queue size, in-flight jobs, worker count).

Enable it via `.nuvom_plugins.toml`.
More: [Prometheus Plugin](docs/plugins.md#prometheus-plugin)

---

## 🧩 Plugin System

All major components — queue, backend, discovery — are pluggable.
Write your own plugins or load third-party ones via `.nuvom_plugins.toml`.

Start here: [Plugin System](docs/plugins.md)

---

## 🛠 Extending Nuvom

Want to register your own result backend or queue engine?
Nuvom makes it easy to implement plugins that hook into its core lifecycle.

Learn how: [Architecture Overview](docs/architecture.md#plugin-architecture)

---

## 🛣 Roadmap

Nuvom follows a milestone-based release cadence.
See: [Roadmap](docs/roadmap.md)

---

## 👥 Contributing

Pull requests are welcome!

See:

- [Architecture Guide](docs/architecture.md)
- [Contributing Instructions](docs/contributing.md)

---

## 🪪 License

Apache 2.0 — use it freely, build responsibly.

---

## 📚 Documentation

Nuvom uses [MkDocs](https://www.mkdocs.org/) with the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme for documentation.

### 🧪 Local Preview

To build and preview the documentation locally:

```bash
hatch shell
mkdocs serve
````

### 📦 Static Site Build

To build the static documentation site:

```bash
mkdocs build
```

### 🧰 Tech Stack

- `mkdocs-material` — for styling and navigation
- `mkdocstrings[python]` — for automated API docs
- `mkdocs-git-revision-date-localized-plugin` — for revision metadata

All documentation dependencies are managed via [Hatch](https://hatch.pypa.io). No need to install anything manually.

---
