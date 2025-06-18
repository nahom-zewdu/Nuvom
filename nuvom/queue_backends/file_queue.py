# nuvom/queue_backends/file_queue.py

"""
File-based job queue implementation storing serialized jobs as files.
Supports atomic file claiming for safe multi-threaded dequeue operations,
batch popping, queue size querying, and cleanup of corrupted or leftover files.
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
from nuvom.log import logger


class FileJobQueue(BaseJobQueue):
    def __init__(self, directory="nuvom_queue"):
        self.dir = directory
        self.lock = Lock()
        os.makedirs(self.dir, exist_ok=True)

    def _job_path(self, job_id: str) -> str:
        """
        Generate a unique file path for a job using timestamp and job ID.
        """
        ts = time.time()
        return os.path.join(self.dir, f"{ts:.6f}_{job_id}.msgpack")

    def _claim_file(self, filepath: str, retries: int = 5, delay: float = 0.05) -> Optional[str]:
        """
        Atomically rename job file to mark it as claimed by this thread.
        Retries multiple times if file is temporarily inaccessible.
        """
        claimed_path = filepath + f".claimed.{uuid.uuid4().hex}"
        for _ in range(retries):
            if not os.path.exists(filepath):
                continue
            try:
                if os.path.exists(filepath):
                    os.rename(filepath, claimed_path)
                    logger.debug(f"Claimed job file: {filepath} -> {claimed_path}")
                    return claimed_path
            except PermissionError:
                time.sleep(delay)
            except FileNotFoundError:
                continue  # Another thread/process claimed or deleted it
        logger.error(f"Failed to claim file: {filepath}")
        return None

    def enqueue(self, job: Job):
        """
        Serialize and write job to the filesystem for processing.
        """
        job_id = job.id
        path = self._job_path(job_id)
        with open(path, "wb") as f:
            f.write(serialize(job.to_dict()))
        logger.info(f"Enqueued job {job_id} at {path}")

    def dequeue(self, timeout=1) -> Optional[Job]:
        """
        Attempt to dequeue one job from the filesystem queue.
        Returns the Job instance or None if none available.
        """
        with self.lock:
            files = sorted(os.listdir(self.dir))
            for filename in files:
                original_path = os.path.join(self.dir, filename)
                claimed_path = self._claim_file(original_path)
                if not claimed_path:
                    continue  # already claimed by another worker

                try:
                    with open(claimed_path, "rb") as f:
                        job_data = deserialize(f.read())
                    safe_remove(claimed_path)
                    job = Job.from_dict(job_data)
                    logger.info(f"Dequeued job {job.id} from {claimed_path}")
                    return job

                except Exception as e:
                    logger.error(f"Failed to process file {claimed_path}: {e}")
                    try:
                        os.rename(claimed_path, claimed_path + ".corrupt")
                        logger.warning(f"Marked corrupt job file: {claimed_path}.corrupt")
                    except Exception:
                        safe_remove(claimed_path)
                    continue
        return None

    def pop_batch(self, batch_size=1, timeout=1) -> List[Job]:
        """
        Pop up to batch_size jobs from the queue atomically.
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
                    job = Job.from_dict(job_data)
                    jobs.append(job)
                    logger.info(f"Popped job {job.id} from batch")
                except Exception as e:
                    logger.error(f"Failed to process job {filename}: {e}")
                    try:
                        if not filename.endswith(".corrupt"):
                            if claimed_path:
                                corrupt_path = f"{claimed_path}.corrupt"
                                if os.path.exists(claimed_path):
                                    os.rename(claimed_path, corrupt_path)
                                    logger.warning(f"Marked corrupt job file: {corrupt_path}")
                            else:
                                logger.error("Failed to claim file and no claimed path available", exc_info=True)
                                continue
                    except PermissionError:
                        logger.error(f"Failed to mark claimed job as corrupt {claimed_path}: {e}")
                        continue
                    except Exception:
                        if claimed_path:
                            safe_remove(claimed_path)
                    continue
        return jobs

    def qsize(self) -> int:
        """
        Return the number of files (jobs) currently in the queue directory.
        """
        size = len(os.listdir(self.dir))
        logger.debug(f"Queue size: {size}")
        return size

    def clear(self):
        """
        Remove all job files in the queue directory.
        """
        for f in os.listdir(self.dir):
            safe_remove(os.path.join(self.dir, f))
        logger.info("Cleared all jobs from file queue")

    def cleanup(self):
        """
        Remove leftover .corrupt and .claimed.* files, e.g. after a crash.
        """
        removed_files = 0
        for fname in os.listdir(self.dir):
            if fname.endswith(".corrupt") or ".claimed" in fname:
                safe_remove(os.path.join(self.dir, fname))
                removed_files += 1
        logger.info(f"Cleaned up {removed_files} leftover corrupt/claimed files")

