# nuvom/utils/file_utils/safe_remove.py

"""
Utility for safely removing a file with retry logic.

Handles transient `PermissionError` (common on Windows or when files are locked)
by retrying deletion before logging an error.
"""

import os
import logging
import time


def safe_remove(path: str, retries: int = 3, delay: float = 0.02):
    """
    Safely delete a file at the given path, with retries for transient errors.

    Args:
        path (str): Path to the file to delete.
        retries (int): Number of times to retry deletion on failure.
        delay (float): Delay (in seconds) between retries.

    Logs:
        Emits an error log if the file cannot be deleted after all retries.
    """
    for _ in range(retries):
        try:
            os.remove(path)
            return
        except PermissionError:
            time.sleep(delay)

    logging.error(f"Failed to delete file after {retries} retries: {path}")
