"""Headless build smoke for the Audio Studio Play Queue dialog (Phase 2)."""

from __future__ import annotations

import pytest
import wx

from quill.core.audio_studio.play_queue import PlayQueue, QueueEntry
from quill.ui.audio_studio.play_queue_dialog import PlayQueueDialog


@pytest.fixture
def app():
    import wx

    a = wx.App(False)
    yield a
    a.Destroy()


def test_dialog_builds(app) -> None:
    q = PlayQueue()
    q.entries = [QueueEntry("a", "A"), QueueEntry("b", "B")]
    dlg = PlayQueueDialog(None, q)
    assert dlg is not None
    dlg.Destroy()


def test_dialog_builds_empty_queue(app) -> None:
    dlg = PlayQueueDialog(None, PlayQueue())
    assert dlg is not None
    dlg.Destroy()


def test_dialog_focusable_controls_have_names(app) -> None:
    """Every focusable control exposes an accessible name (GATE-A11Y)."""
    q = PlayQueue()
    q.entries = [QueueEntry("a", "A")]
    dlg = PlayQueueDialog(None, q)
    try:
        assert dlg._list.GetName() == "Play queue entries"
        for btn in (dlg._add_btn, dlg._next_btn, dlg._remove_btn, dlg._clear_btn):
            assert btn.GetLabel()
        close = dlg.FindWindowById(wx.ID_CLOSE)
        assert close is not None and close.GetLabel()
    finally:
        dlg.Destroy()