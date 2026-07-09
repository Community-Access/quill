"""AIProgressDialog: closing the completed dialog must still run on_ok.

Regression coverage for the Kokoro-download-drops-you-in-the-editor report:
switch_to_ok() only wired its on_ok follow-up (which reopens the Download
Optional Components hub) to the relabeled OK button's click event. Dismissing
the same dialog via the window's close box, Alt+F4, or Escape -- all of which
a screen-reader user reaches for reflexively once they hear the completion
announcement -- fired no button click, so on_ok was silently skipped and the
hub never reopened, leaving focus on the main frame (the editor).
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.ai_transcribe_dialog import AIProgressDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_close_box_after_switch_to_ok_runs_on_ok(wx_app) -> None:
    frame = wx.Frame(None)
    progress = AIProgressDialog(frame, "Downloading Thing", "Preparing download...")

    on_ok_calls = []
    progress.switch_to_ok("Thing is ready.", on_ok=lambda: on_ok_calls.append(True))
    wx_app.ProcessPendingEvents()  # flush the CallAfter that relabels the button

    # Simulate dismissing via the window's own close affordance (X box / Alt+F4 /
    # Escape on some platforms) rather than clicking the relabeled OK button.
    progress.dialog.Close()

    assert on_ok_calls == [True]
    frame.Destroy()


def test_clicking_ok_still_runs_on_ok_exactly_once(wx_app) -> None:
    frame = wx.Frame(None)
    progress = AIProgressDialog(
        frame, "Downloading Thing", "Preparing download...", on_cancel=lambda: None
    )

    on_ok_calls = []
    progress.switch_to_ok("Thing is ready.", on_ok=lambda: on_ok_calls.append(True))
    wx_app.ProcessPendingEvents()  # flush the CallAfter that relabels the button

    btn = progress._cancel_btn
    assert btn is not None
    btn.Command(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId()))

    assert on_ok_calls == [True]
    frame.Destroy()


def test_close_box_before_completion_does_not_call_on_ok(wx_app) -> None:
    frame = wx.Frame(None)
    cancelled = []
    progress = AIProgressDialog(frame, "Downloading Thing", "Preparing download...",
                                 on_cancel=lambda: cancelled.append(True))

    progress.dialog.Close()

    # No switch_to_ok yet -- there is no on_ok to run; closing must not raise.
    frame.Destroy()
