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

def test_discover_multiple_tasks_across_files(tmp_path: Path):
    # ── Arrange ──
    src_dir = tmp_path / "project"
    (src_dir / "module1").mkdir(parents=True)
    (src_dir / "module2").mkdir(parents=True)

    file1 = src_dir / "module1" / "a.py"
    file2 = src_dir / "module2" / "b.py"

    file1.write_text(textwrap.dedent("""
        from nuvom.task import task

        @task
        def task_a():
            pass
    """))

    file2.write_text(textwrap.dedent("""
        from nuvom.task import task

        @task
        def task_b():
            pass
    """))

    # ── Act ──
    tasks = discover_tasks(str(tmp_path))

    # ── Assert ──
    found_names = {t.func_name for t in tasks}
    found_modules = {t.module_name for t in tasks}

    assert found_names == {"task_a", "task_b"}
    assert "project.module1.a" in found_modules
    assert "project.module2.b" in found_modules


def test_discover_respects_exclude_and_nuvomignore(tmp_path: Path):
    # ── Arrange ──
    project_dir = tmp_path / "project"
    (project_dir / "visible").mkdir(parents=True)
    (project_dir / "hidden").mkdir(parents=True)

    visible_file = project_dir / "visible" / "task1.py"
    hidden_file = project_dir / "hidden" / "task2.py"
    ignore_file = project_dir / ".nuvomignore"

    visible_file.write_text(textwrap.dedent("""
        from nuvom.task import task

        @task
        def visible_task():
            pass
    """))

    hidden_file.write_text(textwrap.dedent("""
        from nuvom.task import task

        @task
        def hidden_task():
            pass
    """))

    ignore_file.write_text("hidden/\n")

    # ── Act ──
    tasks = discover_tasks(str(project_dir))

    # ── Assert ──
    task_names = [t.func_name for t in tasks]
    assert "visible_task" in task_names
    assert "hidden_task" not in task_names
