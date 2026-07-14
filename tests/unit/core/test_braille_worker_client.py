"""#244 (BR-021): out-of-process liblouis worker client."""

from __future__ import annotations

import subprocess

import pytest

import quill.core.braille_worker_client as worker
import quill.stability.safe_subprocess as safe_subprocess


def _completed(
    stdout: str = "", returncode: int = 0, stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["worker"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_forward_translate_returns_worker_result(monkeypatch) -> None:
    monkeypatch.setattr(
        safe_subprocess,
        "run_subprocess_safely",
        lambda *_a, **_k: _completed('{"result": ",hello _w"}\n'),
    )
    assert worker.forward_translate("Hello world") == ",hello _w"


def test_back_translate_returns_draft_text(monkeypatch) -> None:
    monkeypatch.setattr(
        safe_subprocess,
        "run_subprocess_safely",
        lambda *_a, **_k: _completed('{"result": "hello world"}'),
    )
    assert worker.back_translate(",hello _w") == "hello world"


def test_timeout_raises_worker_timeout(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="worker", timeout=10.0)

    monkeypatch.setattr(safe_subprocess, "run_subprocess_safely", _boom)
    with pytest.raises(worker.WorkerTimeoutError):
        worker.forward_translate("anything")


def test_worker_crash_is_caught_then_recovers(monkeypatch) -> None:
    calls = {"n": 0}

    def _runner(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _completed(returncode=1, stderr="liblouis segfault")
        return _completed('{"result": "ok"}')

    monkeypatch.setattr(safe_subprocess, "run_subprocess_safely", _runner)
    with pytest.raises(worker.WorkerError):
        worker.forward_translate("first")
    # A fresh subprocess is spawned on the next call, so the worker recovers.
    assert worker.forward_translate("second") == "ok"


def test_error_result_raises_worker_error(monkeypatch) -> None:
    monkeypatch.setattr(
        safe_subprocess,
        "run_subprocess_safely",
        lambda *_a, **_k: _completed('{"error": "liblouis is not installed"}'),
    )
    with pytest.raises(worker.WorkerError, match="liblouis is not installed"):
        worker.forward_translate("x")


def test_worker_status_reports_health(monkeypatch) -> None:
    monkeypatch.setattr(
        safe_subprocess,
        "run_subprocess_safely",
        lambda *_a, **_k: _completed('{"result": "ok"}'),
    )
    worker.forward_translate("x")
    status = worker.worker_status()
    assert status.healthy is True
    assert status.last_alive is not None


def test_back_translate_survives_a_document_too_large_for_argv() -> None:
    """Regression: a live crash report showed a ~450KB BRF file's
    back-translation failing outright (WinError 206, "The filename or
    extension is too long") because the whole document text was packed into
    a single command-line argument to the worker subprocess -- past
    Windows' ~32K CreateProcess command-line-length limit. The payload now
    travels on stdin (no such limit), so a document this size must actually
    launch the real worker subprocess and get a real result, not raise.
    This is a real (unmocked) subprocess call -- liblouis must be installed
    in this environment for it to exercise the actual translation; it is
    skipped otherwise since the point of this test is the transport, not
    liblouis itself.
    """
    large_text = ("hello world " * 40_000).strip()  # ~480KB, well past argv limits
    try:
        result = worker.back_translate(large_text, timeout=30.0)
    except worker.WorkerError as exc:
        if "liblouis is not installed" in str(exc):
            import pytest

            pytest.skip("liblouis is not installed in this environment")
        raise
    assert result
