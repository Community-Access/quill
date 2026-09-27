"""Crash Recovery > Email Support: what the report carries, and where it goes.

#1045/#1046: _send_crash_report must quote the error evidence that justified
the recovery offer, not a fresh log scan. find_error_evidence() re-scans
whatever quill.log looks like *right now*; by the time a user presses the
button the current session's own logging can have pushed the original
evidence out of the scan window. Use offer.error_evidence (captured once, at
offer time) instead.

2026-09-26: the button is "Email Support". It hands a redacted message
addressed to support@community-access.org to the user's own mail program
through the shared support handoff -- never a GitHub issue, and no token.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

import quill.ui.support_dialog as support_dialog_module
from quill.core.recovery import RecoveryOffer
from quill.core.support_message import SUPPORT_EMAIL, build_body, build_mailto_url
from quill.ui.main_frame import MainFrame


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _frame(statuses: list[str], notes: list[str]) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame._show_modal_dialog = lambda _dialog, _label, **_k: wx.ID_YES
    frame._set_status = statuses.append
    frame._record_notification = lambda text, _kind: notes.append(text)
    frame._unclean_exit_context = lambda: "Environment\n  Quill version : test\n"
    frame.ai_support_facts = lambda: {"QUILL AI support ID": "SUP-42"}
    return frame


def _logs(tmp_path: Path) -> Path:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    # A log with no error markers at all -- a fresh find_error_evidence()
    # scan of *this* file would find nothing.
    (logs_dir / "quill.log").write_text(
        "2026-07-15 10:00:00 INFO quill.stability.task_manager: "
        "Task finished operation_id=abc name=lifecycle-idle-sweep duration_ms=0.1\n"
        "api password=hunter2 leaked into a log line\n",
        encoding="utf-8",
    )
    return logs_dir


def _offer(tmp_path: Path) -> RecoveryOffer:
    return RecoveryOffer(
        session_id="prior-session",
        snapshot=tmp_path / "doc.snap",
        error_evidence=(
            "Traceback (most recent call last):\nValueError: this is the captured evidence"
        ),
    )


def test_email_support_mails_the_offers_captured_evidence_to_support(
    wx_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sent: list[tuple[object, object, str]] = []

    def fake_send_by_mail(host, message, *, title="", **_kw):
        sent.append((host, message, title))
        return True

    monkeypatch.setattr(support_dialog_module, "send_by_mail", fake_send_by_mail)
    statuses: list[str] = []
    notes: list[str] = []
    frame = _frame(statuses, notes)
    try:
        closed = MainFrame._send_crash_report(frame, _offer(tmp_path), _logs(tmp_path))
    finally:
        frame.frame.Destroy()

    assert closed is True
    assert len(sent) == 1
    host, message, title = sent[0]
    assert host is frame
    assert title == "Crash Recovery"
    body = build_body(message)
    assert "this is the captured evidence" in body
    assert "Quill version : test" in body
    assert "QUILL AI support ID: SUP-42" in body
    assert "hunter2" not in body
    url, _ = build_mailto_url(message)
    assert url.startswith("mailto:" + SUPPORT_EMAIL)
    assert "github" not in url.lower()
    assert any("mail program" in text for text in statuses)


def test_email_support_keeps_the_dialog_open_when_no_mail_program(
    wx_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(support_dialog_module, "send_by_mail", lambda *_a, **_k: False)
    statuses: list[str] = []
    frame = _frame(statuses, [])
    try:
        closed = MainFrame._send_crash_report(frame, _offer(tmp_path), _logs(tmp_path))
    finally:
        frame.frame.Destroy()

    # False keeps Crash Recovery open; send_by_mail already put the report on
    # the clipboard and said where to write.
    assert closed is False
    assert any("clipboard" in text for text in statuses)
