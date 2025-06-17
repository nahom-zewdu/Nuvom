# tasks/execute_jobs.py
from tasks.jobs import add

job = add.delay(2, 3)
print(f"Job queued with ID: {job.id}")