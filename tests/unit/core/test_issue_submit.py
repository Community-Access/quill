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


# -- feedback_hub version tolerance (2026-08-13, crash fingerprinting) --------
#
# QUILL ships against whatever feedback_hub is installed. 1.1.0 added the
# `fingerprint` and `version_label` parameters; 1.0.x has neither. The submit
# path asks the installed signature what it accepts rather than calling and
# catching TypeError -- a TypeError raised *inside* submit is a real bug, and
# retrying it silently would hide it.


def _fake_hub(monkeypatch, submit_fn) -> list[dict]:
    """Install a fake feedback_hub whose submit records its kwargs."""
    calls: list[dict] = []

    def _record(**kwargs):
        calls.append(kwargs)
        return submit_fn(**kwargs)

    # functools.wraps would copy submit_fn's signature onto _record, which is
    # exactly what the capability probe reads -- so the fake's shape is the
    # shape under test.
    import functools

    wrapped = functools.wraps(submit_fn)(_record)
    fake = types.ModuleType("feedback_hub")
    fake.submit = wrapped  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "feedback_hub", fake)
    monkeypatch.setattr(isub, "target_repo", lambda: "Community-Access/quill")
    return calls


def test_a_modern_feedback_hub_receives_the_fingerprint(monkeypatch) -> None:
    def modern(*, fingerprint="", version_label=False, **_kwargs):
        return "https://github.com/x/y/issues/1", None

    calls = _fake_hub(monkeypatch, modern)

    url, error = isub.submit_crash_issue(
        summary="s", message="m", app_version="1.0", github_token="tok", fingerprint="abc123"
    )

    assert error is None
    assert url
    assert calls[0]["fingerprint"] == "abc123"
    assert calls[0]["version_label"] is True


def test_an_old_feedback_hub_is_never_passed_the_new_parameters(monkeypatch) -> None:
    # 1.0.x: no fingerprint, no version_label. Passing either would raise
    # TypeError and lose the report.
    def legacy(
        *,
        app,
        github_repo,
        github_token,
        summary,
        message,
        category,
        app_version,
        github_labels,
        metadata,
        name="",
        email="",
        db_path=None,
        github_assignee="",
    ):
        return "https://github.com/x/y/issues/2", None

    calls = _fake_hub(monkeypatch, legacy)

    url, error = isub.submit_crash_issue(
        summary="s", message="m", app_version="1.0", github_token="tok", fingerprint="abc123"
    )

    assert error is None
    assert url  # the report is still filed -- it simply is not deduplicated
    assert "fingerprint" not in calls[0]
    assert "version_label" not in calls[0]


def test_an_empty_fingerprint_is_never_sent(monkeypatch) -> None:
    # Empty means "do not deduplicate". Sending it would let feedback_hub
    # treat unrelated reports as the same crash.
    def modern(*, fingerprint="", version_label=False, **_kwargs):
        return "https://github.com/x/y/issues/3", None

    calls = _fake_hub(monkeypatch, modern)

    isub.submit_crash_issue(
        summary="s", message="m", app_version="1.0", github_token="tok", fingerprint=""
    )

    assert "fingerprint" not in calls[0]


def test_a_typeerror_from_inside_submit_is_reported_not_retried(monkeypatch) -> None:
    # The bug the old catch-TypeError-and-retry approach would have hidden.
    def modern(*, fingerprint="", version_label=False, **_kwargs):
        raise TypeError("a real bug inside feedback_hub")

    calls = _fake_hub(monkeypatch, modern)

    url, error = isub.submit_crash_issue(
        summary="s", message="m", app_version="1.0", github_token="tok", fingerprint="abc"
    )

    assert url is None
    assert "a real bug inside feedback_hub" in (error or "")
    assert len(calls) == 1  # reported, not retried


def test_an_unreadable_signature_degrades_to_the_old_call(monkeypatch) -> None:
    # A C-implemented or wrapped submit whose signature cannot be inspected
    # must still file the report, just without deduplication.
    assert isub._submit_parameters(object()) == frozenset()
