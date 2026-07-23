"""Quill Weather background-check Scheduled Task helper. The actual schtasks
calls are Windows-only; these check the command shape and that everything is a
safe no-op off Windows. The schtasks argv is verified by capturing the
safe-subprocess call."""

from __future__ import annotations

import subprocess

from quill.platform.windows import scheduled_task


def test_launch_command_is_the_one_shot_check() -> None:
    cmd = scheduled_task.launch_command()
    assert cmd.strip().endswith("--check-once")
    assert cmd.startswith('"')  # exe path quoted


def test_task_name_is_specific() -> None:
    assert scheduled_task._TASK_NAME == "QuillWeatherAlertCheck"


def test_no_ops_off_windows(monkeypatch) -> None:
    monkeypatch.setattr(scheduled_task, "is_windows", lambda: False)
    assert scheduled_task.register(10) is False
    assert scheduled_task.is_registered() is False
    assert scheduled_task.unregister() is False


def _fake_ok(*_a, **_k) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")


def test_register_builds_a_per_minute_task(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(args, **_kw):
        captured["args"] = list(args)
        return _fake_ok()

    monkeypatch.setattr(scheduled_task, "is_windows", lambda: True)
    monkeypatch.setattr(scheduled_task, "run_subprocess_safely", fake_run)
    assert scheduled_task.register(15) is True
    args = captured["args"]
    assert args[0] == "schtasks"
    assert "/Create" in args
    assert "QuillWeatherAlertCheck" in args
    assert "/SC" in args and "MINUTE" in args
    assert args[args.index("/MO") + 1] == "15"
    assert args[-1] == "/F"  # overwrite an existing task
    assert "--check-once" in args[args.index("/TR") + 1]


def test_register_clamps_interval_to_at_least_one(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(scheduled_task, "is_windows", lambda: True)
    monkeypatch.setattr(
        scheduled_task,
        "run_subprocess_safely",
        lambda args, **_k: captured.update(args=list(args)) or _fake_ok(),
    )
    scheduled_task.register(0)
    assert captured["args"][captured["args"].index("/MO") + 1] == "1"


def test_failure_returns_false(monkeypatch) -> None:
    monkeypatch.setattr(scheduled_task, "is_windows", lambda: True)
    monkeypatch.setattr(
        scheduled_task,
        "run_subprocess_safely",
        lambda args, **_k: subprocess.CompletedProcess([], 1, "", "error"),
    )
    assert scheduled_task.register(10) is False
