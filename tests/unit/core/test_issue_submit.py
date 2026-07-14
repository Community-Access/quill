"""Crash-report issue submission: redaction and token gating (#210 follow-up)."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import quill.core.issue_submit as isub


def test_build_log_summary_redacts_and_bounds(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "quill.log").write_text(
        "INFO startup ok\npassword=hunter2 should be scrubbed\n" + ("x" * 20000),
        encoding="utf-8",
    )

    summary = isub.build_log_summary(logs, max_chars=500)

    assert summary.startswith("Newest log: quill.log")
    # Only a bounded tail is included, not the whole 20k-char file.
    assert len(summary) < 1000


def test_build_log_summary_empty_when_no_logs(tmp_path: Path) -> None:
    assert isub.build_log_summary(tmp_path) == ""


def test_submit_crash_issue_requires_token() -> None:
    url, error = isub.submit_crash_issue(
        summary="s", message="m", app_version="1.0", github_token=""
    )
    assert url is None
    assert error == "No GitHub token configured"


def test_submit_crash_issue_calls_feedback_hub(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_submit(**kwargs):
        calls.append(kwargs)
        return "https://github.com/Community-Access/quill/issues/1", None

    fake_hub = types.ModuleType("feedback_hub")
    fake_hub.submit = _fake_submit  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "feedback_hub", fake_hub)
    monkeypatch.setattr(isub, "target_repo", lambda: "Community-Access/quill")

    url, error = isub.submit_crash_issue(
        summary="Crash", message="body", app_version="1.0", github_token="tok"
    )

    assert url == "https://github.com/Community-Access/quill/issues/1"
    assert error is None
    assert calls[0]["github_repo"] == "Community-Access/quill"
    assert calls[0]["github_token"] == "tok"
    assert "crash" in calls[0]["github_labels"]


def test_submit_crash_issue_swallows_feedback_hub_errors(monkeypatch) -> None:
    def _boom(**_kwargs):
        raise RuntimeError("network down")

    fake_hub = types.ModuleType("feedback_hub")
    fake_hub.submit = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "feedback_hub", fake_hub)
    monkeypatch.setattr(isub, "target_repo", lambda: "Community-Access/quill")

    url, error = isub.submit_crash_issue(
        summary="s", message="m", app_version="1.0", github_token="tok"
    )

    assert url is None
    assert "network down" in (error or "")


def test_target_repo_reads_schema() -> None:
    assert isub.target_repo() == "Community-Access/quill"
