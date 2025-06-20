# tasks/execute_jobs.py
from tasks.jobs import add

jobs = add.map([(2, 3), (3,3), (4,4), (5,5), (6,11), (2, 11), (3,11), (4,11), (5,11), (6,11)])
print(f"Job queued with ID: {jobs}")