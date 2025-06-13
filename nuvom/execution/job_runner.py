# nuvom/execution/job_runner.py

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from nuvom.result_store import set_result, set_error
from nuvom.queue import get_queue_backend
from rich import print

class JobRunner:
    def __init__(self, job, worker_id: int, default_timeout: int):
        self.job = job
        self.worker_id = worker_id
        self.default_timeout = default_timeout
        self.q = get_queue_backend()

    def run(self):
        timeout_secs = self.job.timeout_secs or self.default_timeout
        job = self.job

        # Metadata injection already handled at job creation
        job.mark_running()

        if job.before_job:
            try:
                job.before_job()
            except Exception as e:
                print(f"[yellow][Runner-{self.worker_id}] ⚠️ before_job hook failed: {e}[/yellow]")

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(job.run)
            try:
                result = future.result(timeout=timeout_secs)

                if job.after_job:
                    try:
                        job.after_job(result)
                    except Exception as e:
                        print(f"[yellow][Runner-{self.worker_id}] ⚠️ after_job hook failed: {e}[/yellow]")

                if job.store_result:
                    set_result(job.id, result)
                job.mark_success(result)
                
                return job

            except FutureTimeoutError:
                self._handle_failure("Job execution timed out.")

            except Exception as e:
                self._handle_failure(e)

    def _handle_failure(self, error):
        job = self.job

        if job.on_error:
            try:
                job.on_error(error)
            except Exception as e:
                print(f"[yellow][Runner-{self.worker_id}] ⚠️ on_error hook failed: {e}[/yellow]")

        job.mark_failed(error)

        if job.retries_left > 0:
            print(f"[yellow][Runner-{self.worker_id}] 🔁 Retrying Job {job.func_name} (Retry {job.max_retries - job.retries_left + 1})[/yellow]")
            self.q.enqueue(job)
        else:
            if job.store_result:
                set_error(job.id, str(error))
                job.result = str(error)
            print(f"[red][Runner-{self.worker_id}] ❌ Job {job.func_name} failed after {job.max_retries} retries[/red]")
