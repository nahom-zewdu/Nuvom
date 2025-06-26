# nuvom/execution/job_runner.py

"""
JobRunner executes a single job with timeout handling, lifecycle hooks, retries, 
and result/error persistence. Uses a thread pool for task execution isolation.
"""
import time

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from nuvom.result_store import set_result, set_error
from nuvom.queue import get_queue_backend
from nuvom.log import logger
from nuvom.job import Job
from nuvom.config import get_settings

class JobRunner:
    """
    Executes a job, managing hooks, retries, timeouts, and result storage.

    Args:
        job: The Job instance to execute.
        worker_id: Identifier of the worker running the job.
        default_timeout: Default timeout seconds if job does not specify one.

    Methods:
        run() -> Job: Runs the job with error and retry handling.
    """

    def __init__(self, job, worker_id: int, default_timeout: int):
        self.job = job
        self.worker_id = worker_id
        self.default_timeout = default_timeout
        self.q = get_queue_backend()

    def run(self) -> Job:
        """
        Execute the job with lifecycle hooks and timeout.
        Handles retries and stores results or errors.

        Returns:
            The job instance with updated status.
        """
        timeout_secs = self.job.timeout_secs or self.default_timeout
        job = self.job

        job.mark_running()
        logger.debug(f"[Runner-{self.worker_id}] Starting job '{job.func_name}' with timeout {timeout_secs}s.")

        if job.before_job:
            try:
                job.before_job()
                logger.debug(f"[Runner-{self.worker_id}] before_job hook executed successfully.")
            except Exception as e:
                logger.warning(f"[Runner-{self.worker_id}] before_job hook failed: {e}")

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(job.run)
            try:
                result = future.result(timeout=timeout_secs)

                if job.after_job:
                    try:
                        job.after_job(result)
                        logger.debug(f"[Runner-{self.worker_id}] after_job hook executed successfully.")
                    except Exception as e:
                        logger.warning(f"[Runner-{self.worker_id}] after_job hook failed: {e}")

                if job.store_result:
                    set_result(
                            job_id=job.id,
                            func_name=job.func_name,
                            result=result,
                            args=job.args,
                            kwargs=job.kwargs,
                            retries_left=job.retries_left,
                            attempts=job.max_retries - job.retries_left,
                            created_at=job.created_at,
                            completed_at=time.time(),
                        )

                    logger.debug(f"[Runner-{self.worker_id}] Result stored for job '{job.func_name}'.")

                job.mark_success(result)
                logger.info(f"[Runner-{self.worker_id}] Job '{job.func_name}' completed successfully.")
                return job

            except FutureTimeoutError:
                self._handle_failure("Job execution timed out.")

            except Exception as e:
                self._handle_failure(e)

    def _handle_failure(self, error):
        """
        Handles job failure, runs on_error hook if present,
        marks job as failed, retries if possible, and stores error.

        Args:
            error: The Exception or error message causing failure.
        """
        job = self.job

        if job.on_error:
            try:
                job.on_error(error)
                logger.debug(f"[Runner-{self.worker_id}] on_error hook executed.")
            except Exception as e:
                logger.warning(f"[Runner-{self.worker_id}] on_error hook failed: {e}")

        job.mark_failed(error)

        if job.retries_left > 0:
            job.retries_left -= 1
            retry_count = job.max_retries - job.retries_left
            delay = job.retry_delay_secs or get_settings().retry_delay_secs
            job.next_retry_at = time.time() + delay
            
            logger.warning(f"[Runner-{self.worker_id}] Retrying job '{job.func_name}' (Retry {retry_count}/{job.max_retries}).")
            get_queue_backend().enqueue(job)
        else:
            if job.store_result:
                set_error(
                        job_id=job.id,
                        func_name=job.func_name,
                        error=error,
                        args=job.args,
                        kwargs=job.kwargs,
                        retries_left=job.retries_left,
                        attempts=job.max_retries - job.retries_left,
                        created_at=job.created_at,
                        completed_at=time.time(),
                    )

                job.result = str(error)
            logger.error(f"[Runner-{self.worker_id}] Job '{job.func_name}' failed after {job.max_retries} retries: {error}")
