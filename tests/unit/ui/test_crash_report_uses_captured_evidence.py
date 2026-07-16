"""#1045/#1046: _send_crash_report must file the error evidence that
justified the recovery offer, not a fresh log scan.

find_error_evidence() re-scans whatever quill.log looks like *right now*.
By the time a user actually clicks "Send Bug Report" -- possibly long after
begin_session()'s own gating check -- the current session's own routine
logging can have grown the file enough to push the original evidence out of
the scan window, so a fresh scan finds nothing even though the offer was
correctly justified. Use offer.error_evidence (captured once, at offer
time) instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

import quill.core.feedback_token as feedback_token_module
import quill.core.issue_submit as issue_submit_module
from quill.core.recovery import RecoveryOffer
from quill.ui.main_frame import MainFrame


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_send_crash_report_files_the_offers_captured_evidence(
    wx_app, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    # A log with no error markers at all -- a fresh find_error_evidence()
    # scan of *this* file would find nothing.
    (logs_dir / "quill.log").write_text(
        "2026-07-15 10:00:00 INFO quill.stability.task_manager: "
        "Task finished operation_id=abc name=lifecycle-idle-sweep duration_ms=0.1\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(feedback_token_module, "effective_github_token", lambda: "fake-token")
    captured_calls: list[dict] = []

    def fake_submit_crash_issue(**kwargs: object) -> tuple[str | None, str | None]:
        captured_calls.append(kwargs)
        return "https://github.com/example/example/issues/1", None

    monkeypatch.setattr(issue_submit_module, "submit_crash_issue", fake_submit_crash_issue)

    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame._show_modal_dialog = lambda _dialog, _label, **_k: wx.ID_YES
    frame._set_status = lambda _msg: None
    frame._clear_local_crash_reports = lambda: 0

    offer = RecoveryOffer(
        session_id="prior-session",
        snapshot=tmp_path / "doc.snap",
        error_evidence="Traceback (most recent call last):\nValueError: this is the captured evidence",
    )

    MainFrame._send_crash_report(frame, offer, logs_dir)

    assert len(captured_calls) == 1
    body = captured_calls[0]["message"]
    assert "this is the captured evidence" in body
    frame.frame.Destroy()
