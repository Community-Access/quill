"""Quill Media Player before anything is open (FUX-09).

The Now Playing line names the two commands that begin, with their keys, and
focus lands on it while nothing is open -- not on the Volume slider, which is
where it fell when every transport button was greyed.
"""

from __future__ import annotations

import gc
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.machine_global


@pytest.fixture
def player(quill_data_dir: Path, wx_session_app):
    from quill.apps.player import QuillMediaPlayerFrame

    frame = QuillMediaPlayerFrame()
    try:
        yield frame
    finally:
        # Every clock the window started, as its own close path stops them.
        for timer in [o for o in gc.get_objects() if isinstance(o, wx.Timer)]:
            if timer.IsRunning():
                timer.Stop()
        frame.frame.Destroy()


def test_a_line_before_now_playing_names_what_begins_and_its_keys(player) -> None:
    line = player._first_task_line
    assert line.shown
    assert line.text == (
        "Nothing is open yet. Open File (Ctrl+O) plays a file, or Open Folder as Book "
        "(Ctrl+Shift+O) plays a folder in order."
    )
    assert player._now_playing.GetValue() == "Nothing open."
    # first in the Tab order: made before Now Playing
    children = list(player._now_playing.GetParent().GetChildren())
    assert children.index(line.ctrl) < children.index(player._now_playing)


def test_focus_lands_on_the_line_while_nothing_is_open(player, monkeypatch) -> None:
    focused: list[str] = []
    monkeypatch.setattr(player._first_task_line.ctrl, "SetFocus", lambda: focused.append("line"))
    monkeypatch.setattr(player._player, "SetFocus", lambda: focused.append("transport"))
    player._focus_initial_control()
    assert focused == ["line"]


def test_focus_goes_to_the_transport_once_something_is_open(player, monkeypatch) -> None:
    player._now_playing.SetValue("Garden notes")  # what opening a file does
    assert not player._first_task_line.shown
    focused: list[str] = []
    monkeypatch.setattr(player._first_task_line.ctrl, "SetFocus", lambda: focused.append("line"))
    monkeypatch.setattr(player._player, "SetFocus", lambda: focused.append("transport"))
    player._focus_initial_control()
    assert focused == ["transport"]
