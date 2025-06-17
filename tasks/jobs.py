# tasks/jobs.py
from nuvom.task import task

@task(retries=3, store_result=True, tags=['math'], description='add this shit')
def add(x, y):
    return x + y
