"""Headless build smoke for the Audio Studio Play Queue dialog (Phase 2)."""

from __future__ import annotations

import pytest

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