# Nuvom Scheduling Guide

> Scheduling in Nuvom is a first-class citizen. It works just like `.delay()`, but defers execution for the future or sets up recurring tasks. Jobs are stored in a **scheduler backend**, and workers execute them when they become due.

---

## 1. Concepts

### Schedule Envelope

When you call `.schedule()`, Nuvom wraps your task call in a **ScheduleEnvelope**:

* Contains task name, args/kwargs, schedule type, next run timestamp, and metadata
* Stored in the scheduler backend (a separate queue from the main job queue)
* Scheduler service reads due envelopes and pushes jobs to the main queue

This abstraction allows **reliable, recurring, and time-zone aware scheduling** without burdening the worker logic.

### Scheduling Types

| Type       | Description                                                         | Backend Behavior                                        |
| ---------- | ------------------------------------------------------------------- | ------------------------------------------------------- |
| `one_off`  | Single execution at a specific time (`at`) or after a delay (`in_`) | Removed after dispatch                                  |
| `interval` | Recurring execution every N seconds (`interval`)                    | Next run rescheduled automatically                      |
| `cron`     | Recurring execution following a cron expression (`cron`)            | Scheduler computes next fire time according to timezone |

---

## 2. API Reference

```python
Task.schedule(
    *args,
    at: datetime | None = None,
    in_: timedelta | None = None,
    interval: int | None = None,
    cron: str | None = None,
    timezone_name: str | None = "UTC",
    **kwargs,
) -> ScheduleEnvelope
```

### Parameters

* `*args, **kwargs` — Arguments passed to the task when executed
* `at` — Absolute UTC-aware datetime for one-off execution
* `in_` — Relative `timedelta` from now for one-off execution
* `interval` — Seconds between recurring runs; must be >0
* `cron` — Standard cron string (e.g., `"0 9 * * MON"`)
* `timezone_name` — IANA timezone for cron evaluation; defaults to `"UTC"`

> **Note:** Exactly **one** of `at`, `in_`, `interval`, or `cron` must be provided.

### Returns

* `ScheduleEnvelope` — Backend-storable object representing your scheduled task

---

## 3. Examples

### One-off execution

```python
from datetime import datetime, timezone, timedelta
from tasks import add

# Absolute time
add.schedule(5, 7, at=datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc))

# Relative time
add.schedule(5, 7, in_=timedelta(seconds=30))
```

### Interval execution

```python
# Run every 5 minutes
add.schedule(2, 3, interval=300)
```

### Cron execution

```python
# Run every Monday at 9 AM UTC
add.schedule(1, 2, cron="0 9 * * MON")
```

---

## 4. Scheduler Service

The scheduler backend stores scheduled tasks separately from the main queue. To execute them:

```bash
nuvom runscheduler
```

* Reads `ScheduleEnvelope` objects that are **due**
* Pushes jobs to the main queue for worker consumption
* Reschedules interval and cron tasks automatically
* Supports multiple scheduler instances safely in production

---

## 5. Advanced Notes

### Time Zones

* Cron expressions can be evaluated in any IANA timezone
* Naive `datetime` objects in `at` are assumed UTC with a warning

### Failure & Resilience

* One-off tasks are removed after execution
* Interval tasks are rescheduled automatically, even if the previous run failed
* Scheduler backend implementations can persist envelopes to disk, database, or memory

### Extensibility

* Custom scheduler backends can be implemented by providing `enqueue()`, `get()`, `due()`, `reschedule()`, and `cancel()` methods
* Fully compatible with Nuvom’s plugin system

---

## 6. Best Practices

* Use `.schedule()` over `.delay()` for long-running or recurring tasks
* Combine `.schedule(interval=...)` with `store_result=True` to track recurring job outcomes
* Keep `cron` expressions timezone-aware for production deployments

---
