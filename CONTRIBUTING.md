# Contributing to Nuvom

Thank you for considering contributing to **Nuvom** — a lightweight, plugin-first task execution engine.

We welcome improvements in stability, performance, plugins (new backends, tools, integrations), bug fixes, documentation, and anything else that helps make Nuvom a more reliable, developer-friendly tool.

---

## 📦 Project Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-org/nuvom
   cd nuvom
    ````

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

Most Nuvom components are extensible via base interfaces. To add your own:

### ➕ New Queue Backend

1. Subclass `BaseJobQueue` from `nuvom.queue_backends.base`.
2. Implement required methods: `enqueue`, `dequeue`, `pop_batch`, `qsize`, `clear`.
3. Register it in config or inject dynamically.
4. Add tests under `tests/queue_backends/`.

### ➕ New Result Backend

1. Subclass `BaseResultBackend` from `nuvom.result_backends.base`.
2. Implement: `set_result`, `get_result`, `set_error`, `get_error`.
3. Add tests and update `nuvom.config.get_backend()` if needed.

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

---

## 🧼 Code Style & Linting

Follow [PEP8](https://peps.python.org/pep-0008/) and our custom rules.

We use:

```bash
black .
ruff check .
```

To format and lint your code. Run them before every commit.

---

## 🧠 Logging Guidelines

* Use the centralized `logger` from `nuvom.log`.
* Use `logger.debug` for internals, `logger.info` for job events, `logger.error` for failures.
* Never use `print()` in production code (only allowed in dev CLI experiments or debug flags).

---

## 🧠 Commit Conventions

Use meaningful commit messages. Some examples:

```text
feat(queue): add Redis queue backend support
fix(worker): handle corrupt job file more gracefully
refactor: move logging into centralized logger module
docs: improve README examples and architecture section
```

---

## 📁 Suggested Directory Layout

Keep your modules in these directories:

```text
nuvom/
├── cli/               # CLI entrypoints (Typer commands)
├── queue_backends/    # Your queue logic (File, Memory, etc.)
├── result_backends/   # Result stores
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
* Avoid global state unless absolutely necessary (use singletons sparingly and safely).
* Always consider how a new change fits into the architecture.

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
