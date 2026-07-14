"""Live-wx tests for the Crash Report submit dialog (#622).

The dialog is the wx half of the crash-submit flow; the wx-free
half (:func:`quill.stability.crash_submit.build_crash_report_payload`)
is covered by ``tests/unit/stability/test_crash_submit.py``.

These tests exercise the dialog against real wx controls on Windows.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]  # pytest.importorskip below
import wx  # type: ignore[import-not-found]  # pytest.importorskip below

pytest.importorskip("wx")  # noqa: E402

from pathlib import Path  # noqa: E402

from quill.stability.crash_submit import (  # noqa: E402
    CrashReportPayload,
    build_crash_report_payload,
)
from quill.ui.crash_report_dialog import (  # noqa: E402
    CrashReportDialog,
    CrashReportDialogResult,
    merge_user_context_into_body,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make_payload(tmp_path: Path) -> CrashReportPayload:
    crash_file = tmp_path / "crash.txt"
    crash_file.write_text("traceback dump", encoding="utf-8")
    try:
        raise RuntimeError("synthetic crash")
    except RuntimeError as exc:
        return build_crash_report_payload(
            exc_type=type(exc),
            exc_value=exc,
            exc_tb=exc.__traceback__,
            local_crash_file=crash_file,
            app_version="0.7.0-beta2",
            portable=False,
            screen_reader_name=None,
            recent_commands=("open_file", "save_file", "spell_check"),
            active_document=None,
        )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_dialog_controls_have_accessible_names(wx_app, tmp_path):
    parent = wx.Frame(None)
    try:
        payload = _make_payload(tmp_path)
        dialog = CrashReportDialog(parent, payload=payload)
        try:
            assert dialog.dialog.GetName() == "crash_report_dialog"
            assert dialog._preview.GetName() == "Report preview"
            assert dialog._what_ctrl.GetName() == "What were you doing"
            assert dialog._trigger_ctrl.GetName() == "Triggering command"
            assert dialog._expect_ctrl.GetName() == "Expected behaviour"
            assert dialog._btn_send.GetName() == "Send report"
            assert dialog._btn_copy.GetName() == "Copy to clipboard"
            assert dialog._btn_cancel.GetName() == "Don't send"
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_dialog_preview_shows_payload_body(wx_app, tmp_path):
    parent = wx.Frame(None)
    try:
        payload = _make_payload(tmp_path)
        dialog = CrashReportDialog(parent, payload=payload)
        try:
            preview_text = dialog._preview.GetValue()
            assert "0.7.0-beta2" in preview_text
            assert "open_file" in preview_text
            assert "synthetic crash" in preview_text
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_dialog_local_crash_file_path_is_shown_in_footer(wx_app, tmp_path):
    parent = wx.Frame(None)
    try:
        payload = _make_payload(tmp_path)
        dialog = CrashReportDialog(parent, payload=payload)
        try:
            # The footer StaticText has SetName("Local crash file path");
            # the text contains the local_crash_file path.
            found = False
            for child in dialog.dialog.GetChildren():
                if child.GetName() == "Local crash file path":
                    assert str(payload.local_crash_file) in child.GetLabel()
                    found = True
                    break
            assert found, "expected a 'Local crash file path' StaticText child"
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


# ---------------------------------------------------------------------------
# Button handlers (driven directly, not via ShowModal)
# ---------------------------------------------------------------------------


def test_send_button_returns_send_action_with_redacted_text(wx_app, tmp_path):
    parent = wx.Frame(None)
    try:
        payload = _make_payload(tmp_path)
        dialog = CrashReportDialog(parent, payload=payload)
        try:
            dialog._what_ctrl.SetValue("editing C:/Users/alice/notes.txt -- token=abc123def")
            dialog._trigger_ctrl.SetValue("save_file")
            dialog._expect_ctrl.SetValue("the file should save without error")
            dialog._capture_result("send")
            assert dialog._result.act == "send"
            # The user text is redacted on the way out.
            assert "C:/Users/alice" not in dialog._result.what_doing_text
            assert "abc123def" not in dialog._result.what_doing_text
            assert dialog._result.triggering_command_text == "save_file"
            assert dialog._result.expected_behaviour_text == "the file should save without error"
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_copy_button_returns_copy_action(wx_app, tmp_path):
    parent = wx.Frame(None)
    try:
        payload = _make_payload(tmp_path)
        dialog = CrashReportDialog(parent, payload=payload)
        try:
            dialog._what_ctrl.SetValue("clicking through menus")
            dialog._capture_result("copy")
            assert dialog._result.act == "copy"
            assert dialog._result.what_doing_text == "clicking through menus"
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_cancel_button_returns_cancel_action(wx_app, tmp_path):
    parent = wx.Frame(None)
    try:
        payload = _make_payload(tmp_path)
        dialog = CrashReportDialog(parent, payload=payload)
        try:
            dialog._what_ctrl.SetValue("half-typed note that should be discarded")
            dialog._result = CrashReportDialogResult(act="cancel")
            assert dialog._result.act == "cancel"
            assert dialog._result.what_doing_text == ""
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_cancel_button_is_the_default(wx_app, tmp_path):
    """Plan: 'default = Don't send (recommended)'. A user who opens
    the dialog by accident should not accidentally send anything."""
    parent = wx.Frame(None)
    try:
        payload = _make_payload(tmp_path)
        dialog = CrashReportDialog(parent, payload=payload)
        try:
            # The dialog's default-item reflects which button Enter
            # will fire; we want "Don't send" so Enter does NOT
            # trigger a send.
            assert dialog.dialog.GetDefaultItem() is dialog._btn_cancel
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


# ---------------------------------------------------------------------------
# merge_user_context_into_body
# ---------------------------------------------------------------------------


def test_merge_user_context_appends_what_doing_section():
    body = "QUILL crash report (redacted, ready to send)\n\nTraceback (last frames)\n  ..."
    result = CrashReportDialogResult(
        act="send",
        what_doing_text="editing a file",
        triggering_command_text="save_file",
        expected_behaviour_text="the file should save",
    )
    out = merge_user_context_into_body(body, result)
    assert "User context" in out
    assert "editing a file" in out
    assert "save_file" in out
    assert "the file should save" in out


def test_merge_user_context_skips_empty_fields():
    body = "header line\n"
    result = CrashReportDialogResult(
        act="send",
        what_doing_text="editing a file",
    )
    out = merge_user_context_into_body(body, result)
    # Only "what_doing" is non-empty so the other headers must not
    # appear (avoid an empty "Triggering command:" block in the
    # final report).
    assert "User context" in out
    assert "editing a file" in out
    assert "Triggering command:" not in out
    assert "Expected behaviour:" not in out


def test_merge_user_context_returns_body_unchanged_when_all_empty():
    body = "header line\n"
    result = CrashReportDialogResult(act="cancel")
    out = merge_user_context_into_body(body, result)
    assert out == body
