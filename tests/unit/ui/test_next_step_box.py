"""FUX-16: the failure box offers one next step, and keeps the details behind a button.

The box replaces OK-only boxes whose text was the exception. It must: make
the next step the default button; keep Close free of an access key (Escape
is Close, GATE-14); hide the technical text until asked, let the person edit
it, and copy it without sending anything.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui import next_step_box as nsb


@pytest.fixture
def parent(wx_session_app: Any) -> Any:
    import wx

    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


def test_the_next_step_is_the_default_and_details_start_hidden(parent: Any) -> None:
    box = nsb.NextStepBox(
        parent,
        "Could not open a.txt. The disk is full. Nothing was opened.",
        "Open failed",
        next_label="&Retry",
        details="App: QUILL 1\nError: OSError: x",
    )
    try:
        assert box.next_button.GetLabel() == "&Retry"
        assert box.dialog.GetDefaultItem() is box.next_button
        assert box.close_button.GetLabel() == "Close"  # no access key: Escape is Close
        assert not box.details.IsShown()
        assert "OSError" not in box.message.GetLabel()
        box._on_show()
        assert box.details.IsShown()
        assert box.show_button.GetLabel() == "Hide &Details"
        # The person may take something out before copying (FUX-16: inspect, redact).
        assert box.details.IsEditable()
    finally:
        box.dialog.Destroy()


def test_copy_details_copies_what_is_in_the_field_and_says_nothing_was_sent(
    parent: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.ui.say_commands as say

    copied: list[str] = []
    spoken: list[str] = []
    monkeypatch.setattr(say, "set_clipboard_text", lambda text: copied.append(text) or True)
    box = nsb.NextStepBox(parent, "m", "c", details="original", announce=spoken.append)
    try:
        box.details.SetValue("edited by the person")
        assert box.copy() is True
    finally:
        box.dialog.Destroy()
    assert copied == ["edited by the person"]
    assert spoken == [nsb.COPIED]


def test_no_details_means_no_details_buttons(parent: Any) -> None:
    box = nsb.NextStepBox(parent, "m", "c")
    try:
        assert box.show_button is None
        assert box.copy_button is None
        assert box.next_button is None
        assert box.dialog.GetDefaultItem() is box.close_button
    finally:
        box.dialog.Destroy()


def test_show_next_step_is_true_only_for_the_next_step(parent: Any) -> None:
    import wx

    assert nsb.show_next_step(parent, "m", "c", next_label="&Retry", show_modal=lambda *_: wx.ID_OK)
    assert not nsb.show_next_step(
        parent, "m", "c", next_label="&Retry", show_modal=lambda *_: wx.ID_CANCEL
    )
    assert not nsb.show_next_step(parent, "m", "c", show_modal=lambda *_: wx.ID_OK)
