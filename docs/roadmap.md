# 🛣️ Nuvom Roadmap

This document outlines Nuvom’s development milestones, from initial prototype to the current release, and what’s ahead for v1.0 and beyond.

Nuvom is built to be a **developer-first**, **plugin-friendly**, and **Redis-free** task execution engine. We’re designing for real-world problems across local development, production, and Windows environments — with **predictability**, **extensibility**, and **intuitiveness** at the core.

---

## ✅ Completed Milestones

### v0.1 — Core Foundations

- Basic `@task()` decorator with `.delay()`
- In-memory queue and worker threads
- Functional CLI: `nuvom runworker`, `nuvom list tasks`

---

### v0.2 — Result Backends & CLI

- Pluggable result backend interface
- File-based result store
- Full CLI inspection commands

---

### v0.3 — Queue Backends

- File-based persistent job queue
- Msgpack serialization for jobs
- `.corrupt` quarantine for bad jobs

---

### v0.4 — Runtime Execution & Hooks

- `ExecutionEngine` abstraction
- Timeout and retries
- Lifecycle hooks: `before_job`, `after_job`, `on_error`

---

### v0.5 — Static Task Discovery

- AST-powered task detection
- `.nuvomignore` support
- Manifest system for caching task metadata

---

### v0.6 — Developer Experience Boosts

- Dev mode (`--dev`) for hot task reloading
- Manifest diffing and CLI-rich task listings
- Structured logs and tracebacks via `rich`

---

### v0.7 — Observability & History

- Tracebacks for all jobs
- Full CLI metadata inspection
- Historical job browsing

---

### v0.8 — Reliability and Polish

- Retry-on-failure system
- Timeout policy: `retry`, `fail`, `ignore`
- SDK retry tools
- Job attempt metadata and diagnostics

---

### v0.9 — Plugin Architecture + SQLite

- Fully dynamic plugin system via `.nuvom_plugins.toml`
- SQLite result backend
- Graceful shutdown lifecycle for plugin-based workers
- Plugin-based test coverage

---

## 🚧 Next Release: `v0.10`

> **Status:** Final pre-v1 foundation

- [x] SQLite-based persistent **queue backend**
- [x] Visibility timeout & requeue support
- [x] Plugin regression test suite
- [x] Built-in Prometheus metrics plugin
- [x] MkDocs documentation site
- [x] Performance & concurrency benchmarking
- [x] Plugin lifecycle: `start(settings)`, `stop()`
- [x] Queue introspection metrics: `queue_size`, `inflight_jobs`
- [ ] Final polish + bugfixes for v0.10 release

---

## 🧠 v1.0 Goals — Stable Core

- ✅ Windows-native, Redis-free by design
- ✅ No imports required: safe task discovery via AST
- ✅ CLI-driven, scriptable, and testable
- ✅ Plugin-first queue & result architecture
- ✅ Observability, retries, and timeouts
- 🧩 Plugin registry contracts + third-party plugin showcase
- 📊 Rich dashboard and metrics browser
- 🎯 Queue system stress-tested for multi-core workloads

---

## 🌍 Post‑1.0 Backlog (Ideas)

These features are actively under exploration — not committed to a specific release:

- [ ] Redis queue and result backend (optional, opt-in)
- [ ] Multi-host worker cluster (via file locks or RPC mesh)
- [ ] DAG-style task chaining: `task1().then(task2)`
- [ ] Plugin sandboxing and capability enforcement
- [ ] Web UI / dashboard to browse queue + workers
- [ ] VSCode extension: discover tasks visually, browse results
- [ ] Task versioning and signature integrity check
- [ ] Offline `.nuvom_tasks.json` static task export (zero-import bootstrap)

---

## 📣 Want to Contribute?

The roadmap is shaped by real-world problems. Open an issue or discussion if:

- You need support for a custom backend
- You’re building a dashboard or monitoring tool
- You’re using Nuvom at scale and hitting edge cases
- You want to build your own plugin or backend

Let’s build something lean, sharp, and powerful — together.
