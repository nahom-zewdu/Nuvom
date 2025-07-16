# Contributing to Nuvom

Thank you for considering contributing to **Nuvom** — a lightweight, plugin-first task execution engine.

We welcome improvements in stability, performance, plugins (new backends, tools, integrations), bug fixes, documentation, and anything else that helps make Nuvom a more reliable, developer-friendly tool.

---

## 📦 Project Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/nahom-zewdu/Nuvom
   cd Nuvom
   ```

2. **Install in editable mode:**

   ```bash
   pip install -e .
   ```

3. **Install dev dependencies:**

   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Run tests:**

   ```bash
   pytest
   ```

5. **Try the CLI:**

   ```bash
   nuvom --help
   ```

---

## 🧩 Plugin-Based Development

Most Nuvom components are extensible via base interfaces and the `Plugin` protocol (v0.9+).

To add your own:

### ➕ New Queue Backend

1. Subclass `BaseJobQueue` from `nuvom.queue_backends.base`.
2. Implement required methods: `enqueue`, `dequeue`, `pop_batch`, `qsize`, `clear`.
3. Either:

   * Register the backend name in `.env`, or
   * Create a plugin module and register it via `.nuvom_plugins.toml`.
4. Add tests under `tests/queue_backends/`.

### ➕ New Result Backend

1. Subclass `BaseResultBackend` from `nuvom.result_backends.base`.
2. Implement: `set_result`, `get_result`, `set_error`, `get_error`, `get_full`, `list_jobs`.
3. Register via plugin (preferred) or in `.env`.
4. Add tests under `tests/result_backends/`.

### 🧪 Plugin Testing (v0.9+)

Use the CLI to validate plugin loading:

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

We use `pytest` for testing. All new features **must include tests**.

Run the full test suite:

```bash
pytest
```

Test philosophy:

* Use actual queue + result backends in test scenarios.
* Cover all code paths, including failure cases.
* Test both CLI and programmatic usage.
* For plugin-related code, use isolated `.nuvom_plugins.toml` in `tmp_path`.

---

## 🧼 Code Style & Linting

Follow [PEP8](https://peps.python.org/pep-0008/) and our custom rules.

We use:

```bash
black .
ruff check .
```

Run these before every commit.

---

## 🧠 Logging Guidelines

* Use the centralized `logger` from `nuvom.log`.
* Use `logger.debug` for internals, `logger.info` for job events, `logger.error` for failures.
* Avoid `print()` in production—only for CLI experiments or debug flags.

---

## 🧠 Commit Conventions

Use meaningful commit messages. Examples:

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
├── cli/               # CLI entrypoints (Typer commands)
├── queue_backends/    # Your queue logic (File, Memory, etc.)
├── result_backends/   # Result stores
├── plugins/           # Plugin loader, registry, contracts
├── execution/         # JobRunner and execution context
├── discovery/         # Task discovery and manifest
├── registry/          # Task registry and auto-registration
├── task.py            # Decorator logic
├── config.py          # Pydantic settings loader
├── log.py             # Rich-based logger
├── worker.py          # Worker thread model, Dispatching, retries
```

---

## 🧠 Tips for Contributors

* Think in small, testable units.
* Write docstrings for all public classes and methods.
* Prefer clarity over cleverness.
* Avoid global state unless absolutely necessary.
* Use plugin-based registration when possible for new backends.
* Ensure plugin components follow the `Plugin` protocol contract.

---

## 🤝 Code Review Process

1. Create a PR with a descriptive title and summary.
2. Add relevant tests and update docs if needed.
3. A maintainer will review your PR and request changes if needed.
4. Once approved, it will be merged and included in the next release.

---

## 📬 Need Help?

Feel free to open an issue with questions, bugs, or ideas. PRs are great, but even bug reports and discussions are highly valued.

---

For more details, see the [`README`](/README.md) and [`ARCHITECTURE`](docs/architecture.md).

---

Happy contributing! 🧠💡

---
