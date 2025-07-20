# Nuvom FAQ

Welcome to the Nuvom Frequently Asked Questions. This page answers common questions about how Nuvom works, why it was designed this way, and how to resolve potential issues.

---

## Why doesn’t Nuvom require Redis or a message broker?

Because it doesn’t need one. Nuvom handles queuing and result persistence using **pluggable local backends** like memory, file, and SQLite.

This keeps setup minimal — no servers, no daemons, no Docker.

For larger or distributed use cases, Redis support is planned as a plugin.

---

## Does Nuvom run on Windows?

Yes. Nuvom is **100% Windows-compatible** — no reliance on POSIX signals, `fork()`, or Unix-only libraries. It works on Windows, Linux, and macOS out of the box.

---

## How does task discovery work without importing modules?

Nuvom uses **AST parsing** to detect `@task` decorators. This means:

- No need to import modules
- No side effects from imports
- Safe even in large codebases
- Fast and cacheable (`.nuvom/manifest.json`)

---

## Why isn’t my task showing up?

Check the following:

- Did you run `nuvom discover tasks`?
- Is the file skipped by `.nuvomignore`?
- Is the task defined with `@task` (not a typo)?
- Is the file inside your current working directory?

You can always inspect the manifest manually at `.nuvom/manifest.json`.

---

## My job failed. How do I retry it?

Use either the CLI or the SDK:

**CLI:**

```bash
nuvom inspect job <job_id>
nuvom retry job <job_id>
```

**Python:**

```python
from nuvom.sdk import retry_job
retry_job("<job_id>")
```

---

## How do timeouts and retries work?

Each task can define:

- `timeout_secs`: max execution time
- `retries`: max retry attempts
- `retry_delay_secs`: wait between retries
- `timeout_policy`: `retry`, `fail`, or `ignore`

If a task times out or fails, Nuvom uses these fields to determine what happens next.

---

## How do I test my plugins?

Use the plugin testing CLI:

```bash
nuvom plugin status                      # Show all loaded plugins
nuvom plugin test nuvom_hello.plugin     # Test installed plugin   
nuvom plugin test ./my_plugin.py         # Test from file
```

Make sure your `.nuvom_plugins.toml` file points to a valid Python module implementing the `Plugin` protocol.

---

## Where is job data stored?

Depends on your backend:

- Memory backend: stored in RAM (temporary)
- File backend: stored under `.nuvom/jobs/`
- SQLite backend: stored in `.nuvom/result.db` or as configured

Use `.env` to control storage location and backend type.

---

## My job runs fine manually, but fails in the worker

This usually means:

- The task file isn’t discovered (use `nuvom discover tasks`)
- You have code that assumes global state or one-time imports
- The environment differs (missing `.env` vars or dependencies)

Try running:

```bash
nuvom runtestworker run --job-file myjob.json
```

This simulates a worker run locally.

---

## What can I build with plugins?

Anything:

- Queue backends (e.g., SQLite, Redis, custom API)
- Result backends (file, SQL, S3, etc.)
- Monitoring exporters (Prometheus, JSON logs)
- CLI extensions or pre/post-run hooks

Nuvom's plugin system supports dynamic registration and lifecycle events (`start()`, `stop()`).

---

## Does Nuvom support distributed workers?

Not yet. Current backends (memory, file, SQLite) are designed for **single-host** or **single-disk** usage.

Distributed execution (e.g., multiple machines) will require network-aware backends like Redis or Postgres — coming in post‑v1 releases.

---

## Got a question that’s not listed?

Open an issue on GitHub or reach out via the project discussion board. We’ll update this page as real-world usage evolves.
