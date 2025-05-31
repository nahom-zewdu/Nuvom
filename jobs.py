# # test_jobs.py

# from nuvom import task
# from nuvom.worker import start_worker_pool
# from nuvom.result_store import get_result, get_error

# import threading

# @task(retries=2, store_result=True)
# def add(a, b):
#     return (a + b)

# # Now delay
# jobs = add.map([(2, 4),(2, 3),(26, 4),(72, 4),(82, 4),(29, 4),(0, 4),(92, 45),(22, 4)])

# print("Waiting for result...")
# try:
#     for job in jobs:
#         print(job.get())
# except TimeoutError:
#     print("Job timed out")
# except RuntimeError as e:
#     print("Job failed:", e)
    
    
from nuvom import task

def on_before(job):
    print(f"➡️  About to run {job.func_name}")

def on_after(job, result):
    print(f"✅ {job.func_name} finished with {result}")

def on_error(job, err):
    print(f"❌ {job.func_name} failed: {err}")

@task(retries=1,
      before_job=on_before,
      after_job=on_after,
      on_error=on_error,
      store_result=True)
def div(a, b):
    return a / b

div.delay(10, 2)   # success path
div.delay(10, 0)   # triggers retry + on_error
