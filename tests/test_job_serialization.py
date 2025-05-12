from nuvom.job import Job

def test_job_serialization_roundtrip():
    job = Job(func_name="add", args=(1, 2), kwargs={}, retries=2, store_result=False)
    data = job.to_dict()
    job2 = Job.from_dict(data)
    assert job.id == job2.id
    assert job.func_name == job2.func_name
    assert job.args == job2.args
    assert job.kwargs == job2.kwargs
    assert job.store_result == job2.store_result
