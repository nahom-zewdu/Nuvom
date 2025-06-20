import pytest
from nuvom.registry.registry import get_task_registry

def sample_task():
    return "hello"

def another_task():
    return "world"

def test_register_and_get():
    registry = get_task_registry()
    registry.clear()

    registry.register("test_task", sample_task)
    func = registry.get("test_task")

    assert func is sample_task

def test_all_returns_all_tasks():
    registry = get_task_registry()
    registry.clear()

    registry.register("task1", sample_task)
    registry.register("task2", another_task)

    all_tasks = registry.all()

    assert "task1" in all_tasks
    assert "task2" in all_tasks
    assert all_tasks["task1"].func is sample_task
    assert all_tasks["task2"].func is another_task

def test_clear_removes_all_tasks():
    registry = get_task_registry()
    registry.register("temp_task", sample_task)

    registry.clear()

    assert registry.get("temp_task") is None
    assert registry.all() == {}

def test_duplicate_registration_raises():
    registry = get_task_registry()
    registry.clear()

    registry.register("dup_task", sample_task)
    with pytest.raises(ValueError):
        registry.register("dup_task", another_task)
