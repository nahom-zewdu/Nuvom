# Command-Line Interface (CLI)

Nuvom ships with a powerful developer-first CLI for running workers, inspecting jobs, managing plugins, and more.

Run the following to get started:

```bash
nuvom --help
```

## Worker Control

### Start Worker Threads

```bash
nuvom runworker
```

Starts the dispatcher and worker pool based on your `.env` settings.

---

## Job Inspection & Debugging

### Inspect Job Result

```bash
nuvom inspect job <job_id>
```

View full metadata, result, or traceback for a job.

### Check Status

```bash
nuvom status <job_id>
```

Quickly fetch a job’s final status.

### View Recent History

```bash
nuvom history recent --limit 10 --status SUCCESS
```

See recent jobs by filter or limit.

---

## Task Discovery & Listing

### Discover Tasks

```bash
nuvom discover tasks
```

Parses project source files using AST and updates the manifest.

### List Tasks

```bash
nuvom list tasks
```

Displays all available `@task` functions registered in the manifest.

---

## Local Job Runner

### Run Job Locally (For Testing)

```bash
nuvom runtestworker run --input myjob.json
```

Execute a job directly from a JSON file (offline, no queue).

---

## Plugin Management

### Test Plugins

```bash
nuvom plugin test
```

Attempts to load all plugins from `.nuvom_plugins.toml` and verifies startup/shutdown.

### List Registered Plugins

```bash
nuvom plugin status
```

Shows plugins currently registered by name and type.

### Scaffold Plugin Stub

```bash
nuvom plugin scaffold --type queue_backend --name my_plugin
```

Creates a boilerplate plugin file with the correct structure.

---

## Configuration Helper

```bash
nuvom config
```

Prints all loaded environment variables and configuration values.

---

## 💡 Tips

* Combine `discover tasks` and `list tasks` for troubleshooting discovery issues.
* Use `plugin test` if your backends aren’t being picked up correctly.
* `runtestworker` is useful for debugging serialization or runtime issues offline.
