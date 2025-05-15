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

_shutdown_event = threading.Event()

def worker_loop(worker_id: int, batch_size: int, default_timeout: int):
    q = get_queue_backend()
    
    print(f"[green][ ✔ ] Worker {worker_id} started. {q.qsize()} [/green]")

    while not _shutdown_event.is_set():
        jobs = q.pop_batch(batch_size=batch_size, timeout=default_timeout)
        if not jobs:
            continue

        for job in jobs:
            job.mark_running()
            timeout_secs = job.timeout_secs or default_timeout

            print(f"[blue][Worker-{worker_id}] Running job: {job.to_dict()}[/blue]")

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(job.run)
                try:
                    result = future.result(timeout=timeout_secs)

                    if job.store_result:
                        set_result(job.id, result)
                    job.mark_success(result)

                except FutureTimeoutError:
                    job.mark_failed("Job execution timed out.")

                    if job.store_result:
                        set_error(job.id, "Timed out.")
                    print(f"[red][Worker-{worker_id}] 🕒 Job {job.func_name} timed out after {timeout_secs}s[/red]")

                    if job.can_retry():
                        print(f"[yellow][Worker-{worker_id}] 🔁 Retrying timed-out Job {job.func_name}[/yellow]")
                        q.enqueue(job)

                except Exception as e:
                    job.mark_failed(e)
                    if job.can_retry():
                        print(f"[yellow][Worker-{worker_id}] 🔁 Retrying Job {job.func_name} {job.max_retries - job.retries_left} time [/yellow]")
                        q.enqueue(job)
                    else:
                        if job.store_result:
                            set_error(job.id, str(e))
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
