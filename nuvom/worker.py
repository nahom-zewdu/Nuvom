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
    
    print(f"[green][ ✔ ] Worker {worker_id} started. {q.qsize()} [/green]")
    while not _shutdown_event.is_set():
        jobs = q.pop_batch(batch_size=batch_size, timeout=timeout)
        if not jobs:
            continue
        for job in jobs:
            try:
                print(f"[blue][Worker-{worker_id}] Running job: {job.to_dict()}[/blue]")
                result = job.run()
                store_result(job.id, result)
            except Exception as e:
                retries = job.retries_left
                
                if retries > 0:
                    print(f"[yellow][Worker-{worker_id}] 🔁 Retrying Job {job.func_name} for the {job.max_retries - job.retries_left} time [/yellow]")
                    q = get_global_queue()  
                    q.enqueue(job)  
                else:
                    store_error(job.id, str(e))
                    print(f"[red][Worker-{worker_id}] ❌ Job {job.func_name} failed after {job.max_retries} retries[/red]")


def start_worker_pool():
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
