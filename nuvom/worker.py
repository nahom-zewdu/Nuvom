# nuvom/worker.py

# Pre-spawns worker threads or processes
# Handles job pulling from queue
# Clean shutdown via signals or flags

import threading
import time
from rich import print
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from nuvom.config import get_settings
from nuvom.queue import get_global_queue
from nuvom.result_store import store_result, store_error
_shutdown_event = threading.Event()


def worker_loop(worker_id: int, batch_size: int, timeout: int):
    q = get_global_queue()
    
    while not _shutdown_event.is_set():
        jobs = q.pop_batch(batch_size=batch_size, timeout=timeout)
        print(f"[green][ ✔ ] Worker {worker_id} started. {jobs} [/green]")
        if not jobs:
            continue
        for job in jobs:
            try:
                print(f"[Worker-{worker_id}] Running job: {job}")
                result = job.run()
                store_result(job.id, result)
            except Exception as e:
                store_error(job.id, str(e))
                print(f"[Worker-{worker_id}] Job failed: {e}")


def start_worker_pool():
    settings = get_settings()
    max_workers = settings.max_workers
    batch_size = settings.batch_size
    job_timeout = settings.job_timeout_secs

    print(f"[Nuvom] Starting {max_workers} workers...")
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
