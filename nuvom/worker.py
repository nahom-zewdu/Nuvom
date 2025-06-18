# nuvom/worker.py

import threading
import time
import queue
from typing import List
from rich import print

from nuvom.config import get_settings
from nuvom.queue import get_queue_backend
from nuvom.result_store import set_result, set_error
from nuvom.execution.job_runner import JobRunner
from nuvom.registry.auto_register import auto_register_from_manifest

_shutdown_event = threading.Event()


class WorkerThread(threading.Thread):
    """
    A worker that runs in its own thread, pulls jobs from a personal queue,
    and executes them using JobRunner. It tracks its current load.
    """
    def __init__(self, worker_id: int, job_timeout: int):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.job_timeout = job_timeout
        self._job_queue = queue.Queue()
        self._in_flight = 0
        self._lock = threading.Lock()

    def run(self):
        print(f"[green][ ✔ ] Worker-{self.worker_id} online.[/green]")

        while not _shutdown_event.is_set():
            try:
                job = self._job_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            with self._lock:
                self._in_flight += 1

            print(f"[blue][Worker-{self.worker_id}] Executing job {job.id} ({job.func_name})[/blue]")
            runner = JobRunner(job, worker_id=self.worker_id, default_timeout=self.job_timeout)
            runner.run()
            print(f"[green][Worker-{self.worker_id}] Task: {runner.job.func_name}, args: {runner.job.args}, Result: {runner.job.result}[/green]")

            with self._lock:
                self._in_flight -= 1

    def submit(self, job):
        self._job_queue.put(job)

    def load(self) -> int:
        with self._lock:
            return self._in_flight


class DispatcherThread(threading.Thread):
    """
    Dispatcher pulls job batches from the queue and assigns them to the
    least-loaded WorkerThread.
    """
    def __init__(self, workers: List[WorkerThread], batch_size: int, job_timeout: int):
        super().__init__(daemon=True)
        self.workers = workers
        self.batch_size = batch_size
        self.job_timeout = job_timeout
        self.queue = get_queue_backend()

    def run(self):
        print("[yellow][Dispatcher] Started dispatching jobs.[/yellow]")

        while not _shutdown_event.is_set():
            jobs = self.queue.pop_batch(batch_size=self.batch_size, timeout=self.job_timeout)
            if not jobs:
                continue

            for job in jobs:
                target = min(self.workers, key=lambda w: w.load())
                target.submit(job)
                print(f"[magenta][Dispatcher] Assigned job {job.id} → Worker-{target.worker_id}[/magenta]")


def start_worker_pool():
    """
    Initializes the worker pool and starts the dispatcher loop.
    Auto-registers tasks, then spawns workers and dispatcher.
    """
    auto_register_from_manifest()

    settings = get_settings()
    max_workers = settings.max_workers
    batch_size = settings.batch_size
    job_timeout = settings.job_timeout_secs

    print(f"[blue][Nuvom] Spawning {max_workers} smart workers...[/blue]")

    workers = []
    for i in range(max_workers):
        worker = WorkerThread(worker_id=i, job_timeout=job_timeout)
        worker.start()
        workers.append(worker)

    dispatcher = DispatcherThread(workers=workers, batch_size=batch_size, job_timeout=job_timeout)
    dispatcher.start()

    try:
        while not _shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[red][ ! ] Shutdown requested. Stopping...[/red]")
        _shutdown_event.set()
        dispatcher.join()
        for w in workers:
            w.join()
        print("[green][ ✔ ] All workers stopped cleanly.[/green]")
