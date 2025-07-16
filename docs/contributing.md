# Contributing to Nuvom

Thank you for considering contributing to **Nuvom** — a lightweight, plugin-first task execution engine.

We welcome improvements in stability, performance, plugin support, documentation, bug fixes, and any enhancement that makes Nuvom a more reliable and developer-friendly tool.

---

## 📦 Project Setup (with Hatch)

We use [Hatch](https://hatch.pypa.io) for managing environments, dependencies, testing, and packaging.

### 1. Clone the repository

```bash
git clone https://github.com/nahom-zewdu/Nuvom
cd Nuvom
````

### 2. Install Hatch (once)

```bash
pip install hatch
```

### 3. Enter the development shell

```bash
hatch shell
```

This activates a fully isolated dev environment with all dependencies.

### 4. Run tests

```bash
pytest
```

### 5. Try the CLI

```bash
nuvom --help
```

---

## 🧩 Plugin-Based Development

Most Nuvom components are extensible via base interfaces and the `Plugin` protocol.

### ➕ Add a New Queue Backend

1. Subclass `BaseJobQueue` from `nuvom.queue_backends.base`.
2. Implement:

   * `enqueue`, `dequeue`, `pop_batch`, `qsize`, `clear`
3. Register:

   * via `.env`, or
   * via `.nuvom_plugins.toml` (preferred)
4. Add tests under `tests/queue_backends/`

### ➕ Add a New Result Backend

1. Subclass `BaseResultBackend` from `nuvom.result_backends.base`.
2. Implement:

   * `set_result`, `get_result`, `set_error`, `get_error`, `get_full`, `list_jobs`
3. Register the plugin
4. Add tests under `tests/result_backends/`

---

## 🧪 Plugin Testing

Use the CLI to test plugin loading:

```bash
nuvom plugin test
nuvom plugin list
nuvom plugin inspect <plugin_name>
```

Example `.nuvom_plugins.toml`:

```toml
[plugins]
queue_backend = ["my_module:MyQueuePlugin"]
result_backend = ["my_module:MyResultPlugin"]
```

---

## 🧪 Testing & Coverage

We use `pytest`. All new features **must include tests**.

```bash
pytest
```

**Test philosophy:**

* Use actual backends in test cases
* Cover all logic branches, including edge/failure cases
* Include both CLI and programmatic tests
* For plugin tests, use isolated `.nuvom_plugins.toml` in a temp dir

---

## 🧼 Code Style & Linting

Follow [PEP8](https://peps.python.org/pep-0008/) and our project standards.

### Format & lint code

```bash
hatch run fmt
```

Which runs:

* `black .`
* `ruff check .`

See `pyproject.toml` for configuration.

---

## 🧠 Logging Guidelines

* Use `nuvom.log.logger`, not `print()`
* `logger.debug` → internals
* `logger.info` → lifecycle events (e.g., job started)
* `logger.error` → job or system failures

---

## 📜 Commit Conventions

Use semantic, scoped commit messages. Examples:

```text
feat(plugins): add dynamic plugin registry and loader
feat(result): support SQLite result backend
feat(worker): implement graceful shutdown logic
test(plugin): add test for plugin-registered backend
docs: update CONTRIBUTING for plugin architecture
```

---

## 📁 Suggested Directory Layout

```text
nuvom/
├── cli/               # Typer CLI commands
├── queue_backends/    # Job queues (memory, SQLite, etc.)
├── result_backends/   # Task result stores
├── plugins/           # Loader, registry, capabilities
├── execution/         # JobRunner and context
├── discovery/         # Static task discovery logic
├── registry/          # Task registry and hook system
├── task.py            # @task decorator
├── config.py          # App config loader (pydantic)
├── log.py             # Rich-based logger
├── worker.py          # Worker pool, threading, retry
```

---

## ✅ Best Practices

* Think in small, testable units
* Prefer clarity over cleverness
* Avoid global state unless essential
* Use plugin-based injection when adding new backends
* Document public APIs with docstrings
* Follow the `Plugin` contract for lifecycle integration

---

## 🤝 Code Review Process

1. Fork the repo, create a feature branch
2. Add code and tests
3. Submit a PR with a clear title and description
4. A maintainer will review and provide feedback
5. Once approved, the PR is merged into the main branch

---

## 📬 Need Help?

Feel free to [open an issue](https://github.com/nahom-zewdu/Nuvom/issues) — questions, bugs, and ideas are all welcome.

---

For more context, see [`README.md`](../README.md) and [`docs/architecture.md`](../docs/architecture.md).

---

Happy contributing! 🚀🧠

---
