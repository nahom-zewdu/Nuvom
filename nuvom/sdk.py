# nuvom/sdk.py

from nuvom.result_store import get_backend
from nuvom.queue import enqueue
from nuvom.job import Job

def get_job_status(job_id: str) -> dict:
    """
    Return full metadata about the given job (result or error).
    Raises KeyError if not found.
    """
    backend = get_backend()
    data = backend.get_full(job_id)
    if not data:
        raise KeyError(f"No such job: {job_id}")
    return data

def retry_job(job_id: str) -> str | None:
    """
    Retry a previously failed job, if retries are allowed.
    Returns the new job ID or None if not retryable.
    """
    backend = get_backend()
    snapshot = backend.get_full(job_id)
    if not snapshot:
        raise KeyError(f"No such job: {job_id}")
    
    # Check if job is retryable
    if snapshot["retries_left"] <= 0:
        return None

    # Create a new Job with same func/args
    cloned = Job(
        func_name=snapshot["func_name"],
        args=tuple(snapshot["args"]),
        kwargs=snapshot["kwargs"],
        retries=snapshot["retries_left"],
        store_result=True,
        timeout_secs=snapshot.get("timeout_secs"),
    )
    enqueue(cloned)
    return cloned.id
