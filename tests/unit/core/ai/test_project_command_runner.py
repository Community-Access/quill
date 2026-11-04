"""Running commands for an agent (code.md 4.6, Phase 3 gates)."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from quill.core.ai.command_runner import (
    WARN_DELETES,
    WARN_NETWORK,
    WARN_OUTSIDE,
    AllowList,
    CommandRunner,
    assess_command,
    child_environment,
)


@pytest.mark.parametrize(
    ("command", "warnings"),
    [
        ("pytest -q tests/test_cli.py", ()),
        ("python -m pytest", ()),
        ("npm test", ()),
        ("pip install requests", (WARN_NETWORK,)),
        ("python -m pip install -e .", (WARN_NETWORK,)),
        ("npm install", (WARN_NETWORK,)),
        ("curl https://example.com", (WARN_NETWORK,)),
        ("Invoke-WebRequest https://example.com", (WARN_NETWORK,)),
        ("git pull", (WARN_NETWORK,)),
        ("del build\\out.txt", (WARN_DELETES,)),
        ("rm -rf build", (WARN_DELETES,)),
        ("Remove-Item build -Recurse", (WARN_DELETES,)),
        ("type C:\\Windows\\win.ini", (WARN_OUTSIDE,)),
        ("python ..\\other\\run.py", (WARN_OUTSIDE,)),
    ],
)
def test_warning_lines(tmp_path: Path, command: str, warnings: tuple[str, ...]) -> None:
    assessment = assess_command(command, tmp_path)
    assert assessment.runnable
    assert assessment.warnings == warnings
    assert assessment.may_always_allow == (not warnings)


@pytest.mark.parametrize(
    "command",
    [
        "git push",
        "git push --force origin main",
        "npm publish",
        "twine upload dist/*",
        "cargo publish",
        "reg add HKCU\\Software\\X",
        "Set-ExecutionPolicy Unrestricted",
        "shutdown /s",
        "setx PATH C:\\x",
    ],
)
def test_never_list(tmp_path: Path, command: str) -> None:
    assessment = assess_command(command, tmp_path)
    assert not assessment.runnable
    assert assessment.kept_for_person


def test_environment_carries_no_secrets() -> None:
    base = {
        "PATH": "C:\\bin",
        "GITHUB_TOKEN": "x",
        "COPILOT_GITHUB_TOKEN": "x",
        "OPENAI_API_KEY": "x",
        "AWS_SECRET_ACCESS_KEY": "x",
        "QUILL_DATA_DIR": "x",
        "QUILL_DEV_BUILD": "1",
        "MY_PASSWORD": "x",
        "HOME": "h",
    }
    env = child_environment(base)
    assert env["PATH"] == "C:\\bin" and env["HOME"] == "h"
    for name in base:
        if name not in ("PATH", "HOME"):
            assert name not in env


def test_allow_list_is_outside_the_project_and_exact(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    project_root.mkdir()
    allow = AllowList(tmp_path / "data", "key123")
    assert project_root not in allow.path.parents
    allow.add("pytest")
    assert allow.allows(assess_command("pytest -q tests", project_root))
    assert allow.allows(assess_command("pytest", project_root))
    assert not allow.allows(assess_command("pytestx", project_root))
    allow.add("pip install")  # a person may type it, but a warned command never runs unasked
    assert not allow.allows(assess_command("pip install requests", project_root))
    allow.remove("pytest")
    assert not allow.allows(assess_command("pytest -q", project_root))


def test_a_repository_file_cannot_pre_approve(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    (project_root / ".quill").mkdir(parents=True)
    (project_root / ".quill" / "allowed_commands.json").write_text(
        '{"version": 1, "commands": ["rm -rf ."]}', encoding="utf-8"
    )
    (project_root / "allowed_commands.json").write_text(
        '{"version": 1, "commands": ["python evil.py"]}', encoding="utf-8"
    )
    allow = AllowList(tmp_path / "data", "key123")
    assert allow.entries() == []
    assert not allow.allows(assess_command("python evil.py", project_root))


def test_runs_with_output_to_a_file(tmp_path: Path) -> None:
    runner = CommandRunner(root=tmp_path, output_dir=tmp_path / "out")
    exe = sys.executable
    result = runner.run(f'"{exe}" -c "print(\'hello from the test\')"')
    assert result.exit_code == 0
    assert "hello from the test" in result.output()
    assert result.output_path.parent == tmp_path / "out"


def test_the_child_does_not_see_quill_variables(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SECRET_PROBE", "leak")
    runner = CommandRunner(root=tmp_path, output_dir=tmp_path / "out")
    code = "import os; print(os.environ.get('QUILL_SECRET_PROBE', 'absent'))"
    result = runner.run(f'"{sys.executable}" -c "{code}"')
    assert "absent" in result.output() and "leak" not in result.output()


def test_stop_kills_the_whole_tree_within_two_seconds(tmp_path: Path) -> None:
    marker = tmp_path / "grandchild.pid"
    grandchild = (
        "import time, pathlib, os; "
        f"pathlib.Path(r'{marker}').write_text(str(os.getpid())); time.sleep(60)"
    )
    child = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(60)"
    )
    script = tmp_path / "parent.py"
    script.write_text(child, encoding="utf-8")
    runner = CommandRunner(root=tmp_path, output_dir=tmp_path / "out")
    import threading

    box: dict[str, object] = {}
    worker = threading.Thread(
        target=lambda: box.setdefault("r", runner.run(f'"{sys.executable}" "{script}"'))
    )
    worker.start()
    deadline = time.monotonic() + 20
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert marker.exists(), "the grandchild never started"
    pid = int(marker.read_text())
    started = time.monotonic()
    runner.stop()
    worker.join(10)
    assert not worker.is_alive()
    assert time.monotonic() - started < 2.5
    assert box["r"].stopped  # type: ignore[attr-defined]
    time.sleep(0.3)
    assert not _alive(pid)


def _alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.OpenProcess(
            0x1000 | 0x00100000, False, pid
        )  # QUERY_LIMITED | SYNCHRONIZE
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) != 0
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def test_keep_waiting_no_stops_it(tmp_path: Path) -> None:
    asked: list[float] = []

    def keep_waiting(seconds: float) -> bool:
        asked.append(seconds)
        return False

    runner = CommandRunner(
        root=tmp_path, output_dir=tmp_path / "out", notice_after=0.5, keep_waiting=keep_waiting
    )
    result = runner.run(f'"{sys.executable}" -c "import time; time.sleep(30)"')
    assert asked and result.stopped


def test_the_program_path_is_not_outside_but_an_argument_is(tmp_path: Path) -> None:
    from quill.core.ai.command_runner import WARN_OUTSIDE, assess_command

    program = r'"C:\Program Files\Python\python.exe" -m pytest -q'
    assert WARN_OUTSIDE not in assess_command(program, tmp_path).warnings
    assert WARN_OUTSIDE in assess_command(r"type C:\Windows\win.ini", tmp_path).warnings
