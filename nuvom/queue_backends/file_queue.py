# nuvom/queue_backends/file_queue.py

"""
FileJobQueue provides a file-based persistent job queue backend. 
Jobs are serialized and stored as files in a directory. It handles 
concurrent access with file locking via atomic rename, supports batch
retrieval, and cleans up corrupted or stale job files.

This backend is suitable for lightweight setups without external queue services.
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
    A file-based job queue using the filesystem for persistent job storage and locking.

    Attributes:
        dir (str): Directory path where job files are stored.
        lock (Lock): Thread lock to synchronize queue operations.
    """
    
     # --- Plugin metadata --------------------------------------------------
    api_version = API_VERSION
    name        = "file"
    provides    = ["queue_backend"]
    requires: list[str] = []

    # start/stop are no‑ops for this lightweight backend
    def start(self, settings: dict): ...
    def stop(self): ...

    def __init__(self, directory: str = "nuvom_queue"):
        """
        Initialize the FileJobQueue.

        Args:
            directory (str): Directory to store job files. Created if missing.
        """
        self.dir = directory
        self.lock = Lock()
        os.makedirs(self.dir, exist_ok=True)

    def _job_path(self, job_id: str) -> str:
        """
        Generate a unique job file path using timestamp and job ID.

        Args:
            job_id (str): Unique job identifier.

        Returns:
            str: Full file path for the job.
        """
        ts = time.time()
        return os.path.join(self.dir, f"{ts:.6f}_{job_id}.msgpack")

    def _claim_file(self, filepath: str, retries: int = 5, delay: float = 0.05) -> Optional[str]:
        """
        Atomically rename a job file to mark it as claimed by this thread.

        Args:
            filepath (str): Original job file path.
            retries (int): Number of rename attempts.
            delay (float): Delay between retries in seconds.

        Returns:
            Optional[str]: Claimed file path or None if claiming failed.
        """
        claimed_path = filepath + f".claimed.{uuid.uuid4().hex}"
        for attempt in range(retries):
            if not os.path.exists(filepath):
                continue
            try:
                os.rename(filepath, claimed_path)
                logger.debug(f"Claimed job file '{filepath}' as '{claimed_path}'.")
                return claimed_path
            except PermissionError:
                time.sleep(delay)
            except FileNotFoundError:
                # Another thread/process claimed or deleted the file
                continue
        logger.error(f"Failed to claim job file after {retries} retries: {filepath}")
        return None

    def enqueue(self, job: Job):
        """
        Serialize and save a job to the queue directory.

        Args:
            job (Job): The job instance to enqueue.
        """
        job_id = job.id
        path = self._job_path(job_id)
        with open(path, "wb") as f:
            f.write(serialize(job.to_dict()))
        logger.info(f"Enqueued job '{job_id}' to file '{path}'.")

    def dequeue(self, timeout: int = 1) -> Optional[Job]:
        """
        Remove and return the oldest available job by claiming its file.

        Args:
            timeout (int): Unused in file queue but kept for interface compatibility.

        Returns:
            Optional[Job]: The dequeued job or None if queue is empty.
        """
        with self.lock:
            files = sorted(os.listdir(self.dir))
            for filename in files:
                original_path = os.path.join(self.dir, filename)
                claimed_path = self._claim_file(original_path)
                if not claimed_path:
                    continue  # File already claimed by another thread/process
                try:
                    with open(claimed_path, "rb") as f:
                        job_data = deserialize(f.read())
                    safe_remove(claimed_path)
                    logger.info(f"Dequeued job from '{claimed_path}'.")
                    return Job.from_dict(job_data)
                except Exception as e:
                    logger.error(f"Failed to process claimed job file '{claimed_path}': {e}")
                    try:
                        os.rename(claimed_path, claimed_path + ".corrupt")
                    except Exception:
                        safe_remove(claimed_path)
                    continue
        return None

    def pop_batch(self, batch_size: int = 1, timeout: int = 1) -> List[Job]:
        """
        Remove and return up to `batch_size` jobs from the queue.

        Args:
            batch_size (int): Maximum number of jobs to dequeue.
            timeout (int): Unused for file queue but present for interface compatibility.

        Returns:
            List[Job]: List of dequeued jobs.
        """
        jobs = []
        with self.lock:
            files = sorted(os.listdir(self.dir))[:batch_size]
            claimed_path = ''
            for filename in files:
                if filename.endswith(".corrupt") or ".claimed." in filename:
                    continue  # Skip corrupted or already claimed files
                path = os.path.join(self.dir, filename)
                try:
                    claimed_path = self._claim_file(path)
                    if not claimed_path:
                        continue
                    with open(claimed_path, "rb") as f:
                        job_data = deserialize(f.read())
                    safe_remove(claimed_path)
                    jobs.append(Job.from_dict(job_data))
                    logger.info(f"Popped batch job from '{claimed_path}'.")
                except Exception as e:
                    logger.error(f"Failed to process job file '{filename}': {e}")
                    try:
                        if not filename.endswith(".corrupt"):
                            if claimed_path:
                                corrupt_path = f"{claimed_path}.corrupt"
                                if os.path.exists(claimed_path):
                                    os.rename(claimed_path, corrupt_path)
                                    logger.warning(f"Marked job file as corrupt: {corrupt_path}")
                            else:
                                logger.error("No claimed path available to mark as corrupt.")
                    except PermissionError as pe:
                        logger.error(f"Failed to mark job file as corrupt due to permission: {claimed_path} - {pe}")
                    except Exception:
                        if claimed_path:
                            safe_remove(claimed_path)
                    continue
        return jobs

    def qsize(self) -> int:
        """
        Return the current number of job files in the queue directory.

        Returns:
            int: Number of job files (including possibly corrupt/claimed).
        """
        size = len(os.listdir(self.dir))
        logger.debug(f"Queue size is {size} files.")
        return size

    def clear(self):
        """
        Delete all job files in the queue directory, clearing the queue.
        """
        for f in os.listdir(self.dir):
            path = os.path.join(self.dir, f)
            safe_remove(path)
        logger.info("Cleared all job files from queue directory.")

    def cleanup(self):
        """
        Remove leftover '.corrupt' and '.claimed.*' files from previous crashes or unclean shutdowns.
        """
        for fname in os.listdir(self.dir):
            if fname.endswith(".corrupt") or ".claimed." in fname:
                path = os.path.join(self.dir, fname)
                safe_remove(path)
                logger.info(f"Removed leftover file: {path}")
