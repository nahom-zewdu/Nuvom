"""
FileJobQueue provides a file-based persistent job queue backend.

This backend stores serialized Job objects as individual files in a specified directory.
It supports atomic dequeue via file renaming (to simulate locking), batch popping,
queue size inspection, and cleanup of corrupted or abandoned job files.

This is ideal for lightweight environments or local development without external services.
"""

import uuid
import os
from threading import Lock
from typing import List, Optional
import time

from nuvom.job import Job
from nuvom.queue_backends.base import BaseJobQueue
from nuvom.serialize import serialize, deserialize
from nuvom.utils.file_utils.safe_remove import safe_remove
from nuvom.log import get_logger
from nuvom.plugins.contracts import Plugin, API_VERSION

logger = get_logger()


class FileJobQueue(BaseJobQueue):
    """
    File-based job queue implementation using the filesystem for persistent job storage.

    Jobs are serialized as files and stored in a directory. Thread-safe dequeueing is
    achieved by atomically renaming files. This implementation ensures recoverability
    and visibility into job state.

    Args:
        directory (str): Directory where job files will be stored.
    """

    api_version = API_VERSION
    name = "file"
    provides = ["queue_backend"]
    requires: list[str] = []

    def __init__(self, directory: str = "nuvom_queue"):
        """
        Initialize the job queue and ensure the directory exists.

        Args:
            directory (str): Target directory for storing job files.
        """
        self.dir = directory
        self.lock = Lock()
        os.makedirs(self.dir, exist_ok=True)

    def start(self, settings: dict):
        """No-op for compatibility with plugin interface."""
        ...

    def stop(self):
        """No-op for compatibility with plugin interface."""
        ...

    def _job_path(self, job_id: str) -> str:
        """
        Construct a file path for a job using timestamp and ID.

        Args:
            job_id (str): Unique job identifier.

        Returns:
            str: Full job file path.
        """
        ts = time.time()
        return os.path.join(self.dir, f"{ts:.6f}_{job_id}.msgpack")

    def _claim_file(self, filepath: str, retries: int = 5, delay: float = 0.05) -> Optional[str]:
        """
        Attempt to atomically rename a file to claim it for processing.

        Args:
            filepath (str): Original file path to claim.
            retries (int): Number of retry attempts.
            delay (float): Delay between attempts in seconds.

        Returns:
            Optional[str]: New claimed file path, or None if claim fails.
        """
        claimed_path = filepath + f".claimed.{uuid.uuid4().hex}"
        for _ in range(retries):
            if not os.path.exists(filepath):
                continue
            try:
                os.rename(filepath, claimed_path)
                logger.debug(f"Claimed job file '{filepath}' as '{claimed_path}'.")
                return claimed_path
            except (PermissionError, FileNotFoundError):
                time.sleep(delay)
        logger.error(f"Failed to claim job file: {filepath}")
        return None

    def enqueue(self, job: Job) -> None:
        """
        Serialize and store a job to the queue directory.

        Args:
            job (Job): Job instance to enqueue.
        """
        path = self._job_path(job.id)
        with open(path, "wb") as f:
            f.write(serialize(job.to_dict()))
        logger.info(f"Enqueued job '{job.id}' to file '{path}'.")

    def dequeue(self, timeout: int = 1) -> Optional[Job]:
        """
        Atomically retrieve and remove one job from the queue.

        Args:
            timeout (int): Unused, for interface compatibility.

        Returns:
            Optional[Job]: Deserialized job or None.
        """
        with self.lock:
            for filename in sorted(os.listdir(self.dir)):
                if filename.endswith(".corrupt") or ".claimed." in filename:
                    continue

                original_path = os.path.join(self.dir, filename)
                claimed_path = self._claim_file(original_path)
                if not claimed_path:
                    continue

                try:
                    with open(claimed_path, "rb") as f:
                        job_data = deserialize(f.read())
                    safe_remove(claimed_path)
                    logger.info(f"Dequeued job from '{claimed_path}'.")
                    return Job.from_dict(job_data)
                except Exception as e:
                    logger.error(f"Error reading job file '{claimed_path}': {e}")
                    try:
                        os.rename(claimed_path, claimed_path + ".corrupt")
                    except Exception:
                        safe_remove(claimed_path)
        return None

    def pop_batch(self, batch_size: int = 1, timeout: int = 1) -> List[Job]:
        """
        Atomically retrieve and remove up to `batch_size` jobs from the queue.

        Args:
            batch_size (int): Max number of jobs to return.
            timeout (int): Unused, for interface compatibility.

        Returns:
            List[Job]: List of deserialized Job objects.
        """
        jobs = []
        with self.lock:
            files = sorted(os.listdir(self.dir))
            for filename in files:
                if len(jobs) >= batch_size:
                    break
                if filename.endswith(".corrupt") or ".claimed." in filename:
                    continue

                path = os.path.join(self.dir, filename)
                claimed_path = self._claim_file(path)
                if not claimed_path:
                    continue

                try:
                    with open(claimed_path, "rb") as f:
                        job_data = deserialize(f.read())
                    safe_remove(claimed_path)
                    jobs.append(Job.from_dict(job_data))
                    logger.info(f"Popped batch job from '{claimed_path}'.")
                except Exception as e:
                    logger.error(f"Failed to process batch job '{claimed_path}': {e}")
                    try:
                        os.rename(claimed_path, claimed_path + ".corrupt")
                        logger.warning(f"Marked job file as corrupt: {claimed_path}.corrupt")
                    except Exception:
                        safe_remove(claimed_path)
        return jobs

    def qsize(self) -> int:
        """
        Return number of job files in queue (excluding corrupt).

        Returns:
            int: Number of valid job files.
        """
        try:
            return len([f for f in os.listdir(self.dir) if not f.endswith(".corrupt")])
        except Exception as e:
            logger.error(f"Error counting queue size: {e}")
            return 0

    def clear(self) -> int:
        """
        Delete all job-related files from queue directory.

        Returns:
            int: Number of files removed.
        """
        removed = 0
        for f in os.listdir(self.dir):
            path = os.path.join(self.dir, f)
            try:
                safe_remove(path)
                removed += 1
            except Exception as e:
                logger.warning(f"Failed to delete job file '{path}': {e}")
        logger.info("Cleared all job files from queue directory.")
        return removed

    def cleanup(self) -> int:
        """
        Remove leftover '.corrupt' and '.claimed.*' files from prior crashes.
        """
        remove_count = 0
        
        for fname in os.listdir(self.dir):
            if fname.endswith(".corrupt") or ".claimed." in fname:
                path = os.path.join(self.dir, fname)
                try:
                    safe_remove(path)
                    remove_count += 1
                    logger.info(f"Cleaned up leftover file: {path}")
                except Exception as e:
                    logger.warning(f"Failed to remove leftover file '{path}': {e}")

        return remove_count