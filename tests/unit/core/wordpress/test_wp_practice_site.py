"""The Practice Site's runtime safety: loopback only, its own port, no orphans.

Covers the one plain-HTTP exception (the Practice Site's own loopback port
and nothing else), refusing an occupied port before starting, the ``--require``
preload that pins Playground's listener to 127.0.0.1, a failed start that
says what Playground printed, stopping the whole process tree, and a Reset
confirmation that names every consequence.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from quill.core.wordpress import workbench_practice as wp
from quill.core.wordpress.workbench_practice import (
    PORT,
    PracticeTools,
    is_practice_address,
    port_problem,
    start_command,
    stop_process,
    wait_for_site,
)


def _tools(tmp_path: Path) -> PracticeTools:
    core = tmp_path / "core"
    core.mkdir()
    (core / "wp-load.php").write_text("<?php", encoding="utf-8")
    return PracticeTools(tmp_path / "node.exe", tmp_path / "cli.js", wordpress=core)


@pytest.mark.parametrize(
    "url",
    [f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}/wp-json/", f"http://[::1]:{PORT}"],
)
def test_plain_http_is_allowed_to_the_practice_port_on_this_computer(url: str) -> None:
    assert is_practice_address(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://127.0.0.1:8080",
        f"https://127.0.0.1:{PORT}",  # HTTPS takes the ordinary route, not this exception
        f"http://site.localhost:{PORT}",
        f"http://mysite.test:{PORT}",
        f"http://192.168.1.4:{PORT}",
        f"http://0.0.0.0:{PORT}",
        f"http://127.0.0.1.evil.example:{PORT}",
        "http://127.0.0.1:notaport",
        "",
    ],
)
def test_nothing_else_is_the_practice_site(url: str) -> None:
    assert not is_practice_address(url)


def test_an_occupied_port_is_refused_in_a_sentence() -> None:
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    port = holder.getsockname()[1]
    try:
        said = port_problem(port)
        assert f"port {port}" in said and "already using" in said
    finally:
        holder.close()
    assert port_problem(port) == ""


def test_start_process_refuses_before_spawning_on_an_occupied_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.wordpress.workbench_practice_process as process
    import quill.stability.safe_subprocess as safe

    monkeypatch.setattr(process, "port_problem", lambda _port=PORT: "Port in use.")
    monkeypatch.setattr(
        safe, "spawn_subprocess_safely", lambda *_a, **_k: pytest.fail("spawned anyway")
    )
    with pytest.raises(RuntimeError, match="Port in use."):
        wp.start_process(_tools(tmp_path), tmp_path / "site")


def test_the_command_preloads_the_loopback_pin(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    argv = start_command(tools, tmp_path / "site")
    preload = tmp_path / "site" / "loopback-only.cjs"
    assert argv[1:3] == ["--require", str(preload)]
    assert argv[3] == str(tools.cli), "node options come before the script"
    assert "127.0.0.1" in preload.read_text(encoding="utf-8")
    assert f"--site-url=http://127.0.0.1:{PORT}" in argv


def test_every_start_lets_application_passwords_work_over_loopback(tmp_path: Path) -> None:
    """WordPress refuses app passwords over plain HTTP unless something allows them."""
    tools = _tools(tmp_path)
    plugin = (
        tmp_path / "site" / "wordpress" / "wp-content" / "mu-plugins" / "quill-practice-site.php"
    )
    start_command(tools, tmp_path / "site")
    assert "wp_is_application_passwords_available" in plugin.read_text(encoding="utf-8")
    plugin.unlink()
    start_command(tools, tmp_path / "site")  # an already-set-up site gets it back
    assert plugin.is_file()


def test_no_auto_login_to_block_the_rest_client(tmp_path: Path) -> None:
    argv = start_command(_tools(tmp_path), tmp_path / "site")
    assert "--login" not in argv
    assert all(step["step"] != "login" for step in wp.blueprint()["steps"])  # type: ignore[union-attr]


def _node() -> str | None:
    staged = Path(__file__).resolve().parents[4] / "build" / "deps" / "nodejs" / "node.exe"
    return str(staged) if staged.is_file() else shutil.which("node")


@pytest.mark.skipif(_node() is None, reason="no Node.js on this machine")
@pytest.mark.parametrize(
    "call",
    [
        "server.listen(0, report)",
        "server.listen({port: 0}, report)",
        "server.listen(0, '0.0.0.0', report)",
        "server.listen(report)",
        "server.listen(0, 5, report)",
    ],
)
def test_the_preload_really_pins_node_to_loopback(tmp_path: Path, call: str) -> None:
    start_command(_tools(tmp_path), tmp_path / "site")
    preload = tmp_path / "site" / "loopback-only.cjs"
    script = (
        "const net = require('net'); const server = net.createServer();"
        "function report() { console.log(server.address().address); server.close(); }"
        f"{call};"
    )
    result = subprocess.run(  # noqa: S603 - a fixed Node and an inline test script
        [_node(), "--require", str(preload), "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert result.stdout.strip() == "127.0.0.1"


class _Exited:
    pid = 0
    stdin = stdout = stderr = None

    def __init__(self, tail: list[str]) -> None:
        self._quill_tail = tail

    def poll(self) -> int:
        return 1


def test_a_failed_start_says_what_playground_printed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError) as caught:
        wait_for_site(_Exited(["noise", "Error: PHP failed to boot"]), tmp_path, timeout=1)
    said = str(caught.value)
    assert "stopped before WordPress was ready" in said
    assert "PHP failed to boot" in said and "noise" not in said


_PARENT = (
    "import subprocess, sys, time;"
    "sys.stdin.readline();"  # wait until the test has put this process in its job
    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']);"
    "print(child.pid, flush=True); time.sleep(120)"
)


def _spawn_with_child(*, job: bool) -> tuple[subprocess.Popen[bytes], int, object]:
    from quill.core.radio.recording_winjob import assign_kill_on_close_job

    process = subprocess.Popen(  # noqa: S603 - this interpreter, an inline script
        [sys.executable, "-c", _PARENT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    handle = assign_kill_on_close_job(process) if job else None
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(b"go\n")
    process.stdin.flush()
    child = int(process.stdout.readline().decode().strip())
    return process, child, handle


def _gone(psutil, pid: int) -> bool:  # type: ignore[no-untyped-def]
    try:
        psutil.Process(pid).wait(timeout=10)
    except psutil.NoSuchProcess:
        return True
    except psutil.TimeoutExpired:
        return False
    return True


def _cleanup(psutil, process: subprocess.Popen[bytes], child: int) -> None:  # type: ignore[no-untyped-def]
    if process.poll() is None:
        process.kill()
    try:
        psutil.Process(child).kill()
    except psutil.Error:
        pass


@pytest.mark.skipif(sys.platform != "win32", reason="taskkill /T is Windows")
def test_stop_ends_the_whole_process_tree() -> None:
    psutil = pytest.importorskip("psutil")
    process, child, _ = _spawn_with_child(job=False)
    try:
        stop_process(process, timeout=10)
        assert process.poll() is not None
        assert _gone(psutil, child), "the child outlived the stop"
    finally:
        _cleanup(psutil, process, child)


@pytest.mark.skipif(sys.platform != "win32", reason="job objects are Windows")
def test_a_dying_quill_takes_the_tree_with_it() -> None:
    """Closing the job handle is what the OS does when QUILL crashes."""
    psutil = pytest.importorskip("psutil")
    from quill.core.radio.recording_winjob import close_job_handle

    process, child, handle = _spawn_with_child(job=True)
    try:
        assert handle, "a kill-on-close job could not be made here"
        close_job_handle(handle)
        assert process.wait(timeout=10) is not None
        assert _gone(psutil, child), "the child outlived its job"
    finally:
        _cleanup(psutil, process, child)


def test_reset_names_every_consequence() -> None:
    from quill.ui.wordpress_workbench_bold_practice import RESET_WARNING

    for words in (
        "permanently deletes",
        "post",
        "upload",
        "Credential Manager",
        "real WordPress sites are not touched",
        "cannot be undone",
    ):
        assert words in RESET_WARNING, words
