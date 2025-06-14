# tests/test_discovery.py

import textwrap
from pathlib import Path
from nuvom.discovery.discover_tasks import discover_tasks

def test_discover_single_task(tmp_path: Path):
    # ── Arrange ──
    src_dir = tmp_path / "myapp"
    src_dir.mkdir()
    task_file = src_dir / "jobs.py"
    task_file.write_text(textwrap.dedent("""
        from nuvom.task import task

        @task
        def say_hello(name):
            return f"Hello, {name}"
    """))

    # ── Act ──
    tasks = discover_tasks(root_path=str(tmp_path))
    # ── Assert ──
    assert len(tasks) == 1
    task = tasks[0]
    print('========', task.module_name)
    assert task.func_name == "say_hello"
    assert task.file_path.endswith("jobs.py")
    assert task.module_name == "myapp.jobs"
