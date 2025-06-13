# nuvom/worker.py

# Pre-spawns worker threads or processes
# Handles job pulling from queue
# Clean shutdown via signals or flags

import threading
import time
from rich import print
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from nuvom.config import get_settings
from nuvom.queue import get_queue_backend
from nuvom.result_store import set_result, set_error
from nuvom.execution.job_runner import JobRunner
from nuvom.registry.auto_register import auto_register_from_manifest

_shutdown_event = threading.Event()

def worker_loop(worker_id: int, batch_size: int, default_timeout: int):
    q = get_queue_backend()
    
    print(f"[green][ ✔ ] Worker {worker_id} started. {q.qsize()} [/green]")

    while not _shutdown_event.is_set():
        jobs = q.pop_batch(batch_size=batch_size, timeout=default_timeout)
        if not jobs:
            continue

        for job in jobs:
            print(f"[blue][Worker-{worker_id}] Executing job {job.id} ({job.func_name})[/blue]")
            runner = JobRunner(job, worker_id=worker_id, default_timeout=default_timeout)
            runner.run()

def start_worker_pool():
    
    auto_register_from_manifest() # Auto-register all discovered tasks from the manifest into the global task registry.

    settings = get_settings()
    max_workers = settings.max_workers
    batch_size = settings.batch_size
    job_timeout = settings.job_timeout_secs

    print(f"[blue][Nuvom] Starting {max_workers} workers...[/blue]")
    threads = []

    for worker_id in range(max_workers):
        thread = threading.Thread(
            target=worker_loop,
            args=(worker_id, batch_size, job_timeout),
            daemon=True,
        )
        threads.append(thread)
        thread.start()

    try:
        while not _shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[red][ ! ] Shutdown requested. Stopping workers...[/red]")
        _shutdown_event.set()
        for t in threads:
            t.join()
        print("[green][ ✔ ] All workers stopped.[/green]")
