# nuvom/utils/file_utils/safe_remove.py

import os
import logging
import time

def safe_remove(path, retries=3, delay=0.02):
    for _ in range(retries):
        try:
            os.remove(path)
            return
        except PermissionError:
            time.sleep(delay)
    logging.error(f"Failed to delete file after retries: {path}")
