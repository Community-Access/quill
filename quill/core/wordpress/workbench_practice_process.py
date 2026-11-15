"""Running the Practice Site's server: its port, start, readiness and stop.

Split from :mod:`quill.core.wordpress.workbench_practice` (GATE-11), which
re-exports every name here, so callers keep importing from there. This half
owns the process: it refuses an occupied port (:func:`port_problem`), starts
Playground on loopback in a Windows kill-on-close job with its output drained
(:func:`start_process`), waits for WordPress and the first-run setup
(:func:`wait_for_site`), and stops the whole process tree
(:func:`stop_process`). Wx-free.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from http.client import HTTPConnection
from pathlib import Path

from quill.core.wordpress.workbench_practice import (
    _HANDOFF_DIR,
    _PASSWORD_FILE,
    _SETUP_MARKER,
    LOOPBACK_HOST,
    PORT,
    PRACTICE_NAME,
    PracticeTools,
    site_url,
    start_command,
)

__all__ = [
    "last_output",
    "port_problem",
    "start_process",
    "stop_process",
    "wait_for_site",
]


def port_problem(port: int = PORT) -> str:
    """Why the practice site cannot listen on *port* now, or "" when it can.

    Checked before starting, because Playground quietly picks another port
    when its own is taken, and QUILL would then be talking to whatever holds
    9400 -- possibly an earlier Practice Site, possibly something else.
    """
    import socket

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(0.5)
    try:
        answered = probe.connect_ex((LOOPBACK_HOST, port)) == 0
    except OSError:
        answered = False
    finally:
        probe.close()
    if not answered:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind((LOOPBACK_HOST, port))
        except OSError:
            answered = True
        finally:
            listener.close()
    if not answered:
        return ""
    return (
        f"Something on this computer is already using port {port}, which the Practice "
        "Site needs. If another copy of QUILL or QUILL Lite has its Practice Site "
        "running, stop it there first, then start this one again."
    )


def wait_for_site(
    process: subprocess.Popen[bytes], folder: Path, *, port: int = PORT, timeout: float = 300.0
) -> None:
    """Wait until the local REST index and the first-run setup are ready.

    PHP in WebAssembly is slow: the REST index takes two to four seconds to
    build even when asked only for its name, address and namespaces, so each
    probe may wait up to 15 seconds, and a first start (WordPress installing
    itself into SQLite, then the blueprint) gets five minutes in all; it took
    nearly three in the 2026-11-13 live run.
    """
    deadline = time.monotonic() + max(0.0, timeout)
    handoff = folder / _HANDOFF_DIR
    while True:
        if process.poll() is not None:
            said = last_output(process)
            raise RuntimeError(
                "The Practice Site stopped before WordPress was ready."
                + (f" It said: {said}" if said else "")
                + " Start it again, or reset it if this keeps happening."
            )
        connection = HTTPConnection(LOOPBACK_HOST, port, timeout=15.0)
        try:
            connection.request("GET", "/wp-json/?_fields=name,url,namespaces")
            response = connection.getresponse()
            index = json.loads(response.read().decode("utf-8")) if response.status == 200 else {}
            namespaces = index.get("namespaces") if isinstance(index, dict) else None
            initialized = (handoff / _SETUP_MARKER).is_file() or (
                handoff / _PASSWORD_FILE
            ).is_file()
            if (
                isinstance(namespaces, list)
                and "wp/v2" in namespaces
                and str(index.get("name", "")) == PRACTICE_NAME
                and str(index.get("url", "")).rstrip("/") == site_url(port)
                and initialized
            ):
                return
        except (OSError, ValueError):
            pass
        finally:
            connection.close()
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"The Practice Site did not become ready within {round(timeout)} seconds, "
                "so QUILL stopped it. Start it again; if it still does not start, reset it."
            )
        time.sleep(0.25)


def start_process(
    tools: PracticeTools, folder: Path, *, port: int = PORT
) -> subprocess.Popen[bytes]:
    """Start Playground on loopback, tied to QUILL's lifetime, its pipes drained.

    Refuses plainly when the port is taken. On Windows the process goes in a
    kill-on-close job object, so a crashed QUILL cannot leave a server (or
    anything it started) running with nobody to stop it. Its output is read
    continuously -- an unread pipe fills and freezes the server -- and the
    last few lines are kept for a failed start's explanation.
    """
    problem = port_problem(port)
    if problem:
        raise RuntimeError(problem)
    argv = start_command(tools, folder, port=port)
    from quill.core.radio.recording_winjob import assign_kill_on_close_job
    from quill.stability.safe_subprocess import spawn_subprocess_safely

    process = spawn_subprocess_safely(argv, cwd=str(folder))
    process._quill_job = assign_kill_on_close_job(process)  # type: ignore[attr-defined]
    _drain(process)
    return process


def _drain(process: subprocess.Popen[bytes]) -> None:
    import collections
    import threading

    tail: collections.deque[str] = collections.deque(maxlen=20)

    def read(stream: object) -> None:
        try:
            for raw in iter(stream.readline, b""):  # type: ignore[attr-defined]
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    tail.append(line)
        except (OSError, ValueError):
            pass

    threads = [
        threading.Thread(target=read, args=(s,), daemon=True, name="practice-site-output")
        for s in (process.stdout, process.stderr)
        if s is not None
    ]
    for thread in threads:
        thread.start()
    process._quill_tail = tail  # type: ignore[attr-defined]
    process._quill_readers = threads  # type: ignore[attr-defined]


def last_output(process: subprocess.Popen[bytes]) -> str:
    """The last line Playground printed, for a failed start's sentence ("" if none)."""
    tail = getattr(process, "_quill_tail", None)
    return str(tail[-1])[:300] if tail else ""


def _kill_tree(process: subprocess.Popen[bytes]) -> None:
    """End the process and everything it started, and close its job.

    Windows: ``taskkill /T`` walks the tree while the parent still lives;
    closing the kill-on-close job then ends anything that escaped the walk
    (the same job is what ends the tree when QUILL itself dies).
    """
    if os.name == "nt" and process.poll() is None:
        from quill.stability.safe_subprocess import run_subprocess_safely

        taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
        try:
            run_subprocess_safely(
                [str(taskkill), "/PID", str(process.pid), "/T", "/F"], timeout_seconds=10.0
            )
        except Exception:  # noqa: BLE001 - the job and kill() below still apply
            pass
    job = getattr(process, "_quill_job", None)
    if job:
        from quill.core.radio.recording_winjob import close_job_handle

        process._quill_job = None  # type: ignore[attr-defined]
        close_job_handle(job)  # kill-on-close: the OS ends every process in the job
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


def stop_process(process: subprocess.Popen[bytes], *, timeout: float = 5.0) -> None:
    """Stop Playground and every process under it; never leave one behind."""
    if process.poll() is None:
        if os.name == "nt":
            _kill_tree(process)  # TerminateProcess is never graceful on Windows anyway
        else:
            try:
                process.terminate()
            except OSError:
                pass
        try:
            process.wait(timeout=max(0.0, timeout))
        except subprocess.TimeoutExpired:
            _kill_tree(process)
            try:
                process.wait(timeout=max(0.0, timeout))
            except subprocess.TimeoutExpired:
                pass
    job = getattr(process, "_quill_job", None)
    if job:
        _kill_tree(process)  # it exited; closing the job ends anything it left
    for reader in getattr(process, "_quill_readers", ()):
        reader.join(timeout=1.0)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
