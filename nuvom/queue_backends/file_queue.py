# nuvom/queue_backends/file_queue.py

import uuid
import os
from threading import Lock
from typing import List, Optional
import time
import logging

from nuvom.job import Job
from nuvom.queue_backends.base import BaseJobQueue
from nuvom.serialize import serialize, deserialize
from nuvom.utils.file_utils.safe_remove import safe_remove

class FileJobQueue(BaseJobQueue):
    def __init__(self, directory="nuvom_queue"):
        self.dir = directory
        self.lock = Lock()
        os.makedirs(self.dir, exist_ok=True)

    def _job_path(self, job_id):
        ts = time.time()
        return os.path.join(self.dir, f"{ts:.6f}_{job_id}.msgpack")
    
    def _claim_file(self, filepath, retries=5, delay=0.05):
        """Atomically rename job file to mark it as claimed by this thread."""
        claimed_path = filepath + f".claimed.{uuid.uuid4().hex}"
        for _ in range(retries):
            if not os.path.exists(filepath):
                continue
            try:
                if os.path.exists(filepath):
                    os.rename(filepath, claimed_path)
                    return claimed_path
            except PermissionError:
                time.sleep(delay)
            except FileNotFoundError:
                continue  # Someone else claimed or deleted it
        logging.error(f"Failed to claim file: {filepath}")

    def enqueue(self, job: Job):
        job_id = job.id
        with open(self._job_path(job_id), "wb") as f:
            f.write(serialize(job.to_dict()))

    def dequeue(self, timeout=1) -> Optional[Job]:
        with self.lock:
            files = sorted(os.listdir(self.dir))
            for filename in files:
                original_path = os.path.join(self.dir, filename)
                claimed_path = self._claim_file(original_path)
                if not claimed_path:
                    continue  # already taken

                try:
                    with open(claimed_path, "rb") as f:
                        job_data = deserialize(f.read())
                    safe_remove(claimed_path)
                    return Job.from_dict(job_data)

                except Exception as e:
                    logging.error(f"Failed to process file {claimed_path}: {e}")
                    try:
                        os.rename(claimed_path, claimed_path + ".corrupt")
                    except Exception:
                        safe_remove(claimed_path)
                    continue
        return None


    def pop_batch(self, batch_size=1, timeout=1) -> List[Job]:
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
                except Exception as e:
                    logging.error(f"Failed to process job {filename}: {e}")
                    try:
                        if not filename.endswith(".corrupt"):
                            if claimed_path: # type: ignore
                                corrupt_path = f"{claimed_path}.corrupt"
                            else:
                                logging.error("Failed to claim file and no claimed path available", exc_info=True)
                                continue
                            try:
                                if os.path.exists(claimed_path):
                                    os.rename(claimed_path, corrupt_path)
                            except PermissionError:
                                logging.error(f"Failed to mark claimed job as corrupt {claimed_path}: {e}")
                                continue
                    except Exception:
                        if claimed_path: # type: ignore
                            safe_remove(claimed_path)
                    continue
        return jobs

    def qsize(self) -> int:
        return len(os.listdir(self.dir))

    def clear(self):
        for f in os.listdir(self.dir):
            safe_remove(os.path.join(self.dir, f))

    def cleanup(self):
        """Remove leftover .corrupt and .claimed.* files (e.g. after crash)."""
        for fname in os.listdir(self.dir):
            if fname.endswith(".corrupt") or ".claimed" in fname:
                safe_remove(os.path.join(self.dir, fname))
