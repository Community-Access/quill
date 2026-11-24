"""Cast's first useful task at launch (FUX-09).

The empty Podcasts place said what fills it while the window was still being
built, before it was on screen and before the welcome opened over it, and was
silent after the welcome closed. Now it is quiet while building and said once,
on the landing place, after the welcome is answered -- or not at all when the
welcome's Add Your First Podcast is opening.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def later(monkeypatch):
    """wx.CallLater, run inline and recorded: (milliseconds, ...)."""
    calls: list[int] = []

    def call_later(ms, fn, *args):
        calls.append(ms)
        fn(*args)

    from quill.ui.podcasts import launch_first_task

    monkeypatch.setattr(launch_first_task, "_later", call_later)
    return calls


def test_the_podcasts_place_names_add_podcast_its_key_and_the_internet() -> None:
    from quill.core.podcasts import places as places_model
    from quill.core.podcasts.subscriptions import PodcastLibrary

    said = places_model.empty_state(PodcastLibrary(), "podcasts")
    assert said.startswith("No podcasts yet. Add Podcast (Ctrl+N)")
    assert "over the internet" in said
    assert "Import OPML" not in said  # hidden in Simple menus, the default


class _Host:
    def __init__(self, *, shown: bool = True, active: bool = True) -> None:
        self.frame = SimpleNamespace(IsShown=lambda: shown, IsActive=lambda: active)
        self._current_place = "podcasts"
        self.focused: list[str] = []
        self._content = SimpleNamespace(focus=lambda: self.focused.append("content"))
        self.said: list[str] = []
        self._place_announced_empty = "podcasts"  # the quiet launch arrival

    def _say_empty_place_once(self, place_id: str) -> None:
        if self._place_announced_empty != place_id:
            self._place_announced_empty = place_id
            self.said.append(place_id)


def test_after_the_window_is_up_the_landing_place_is_focused_and_said_once(later) -> None:
    from quill.ui.podcasts.launch_first_task import SAY_AFTER_MS, say_landing_place

    host = _Host()
    say_landing_place(host)
    assert host.focused == ["content"]
    assert host.said == ["podcasts"]
    # after the screen reader's own focus speech, not on top of it
    assert later == [SAY_AFTER_MS]


def test_nothing_is_said_when_another_window_is_in_front_by_then(later) -> None:
    from quill.ui.podcasts.launch_first_task import say_landing_place

    host = _Host(active=False)
    say_landing_place(host)
    assert host.said == []


def test_nothing_is_said_from_the_tray_or_over_add_podcast(later) -> None:
    from quill.ui.podcasts.launch_first_task import say_landing_place

    tray = _Host(shown=False)
    say_landing_place(tray)
    assert tray.said == [] and tray.focused == []
    adding = _Host()
    adding._cast_adding_first_podcast = True
    say_landing_place(adding)
    assert adding.said == []


def test_the_welcome_runs_first_then_the_landing_place(monkeypatch, later) -> None:
    from quill.ui.podcasts import first_run_dialog, launch_first_task

    order: list[str] = []
    host = _Host()
    monkeypatch.setattr(first_run_dialog, "maybe_run_first_run", lambda _h: order.append("welcome"))
    host._say_empty_place_once = lambda place: order.append(f"say {place}")
    launch_first_task.launch_first_task(host)
    assert order == ["welcome", "say podcasts"]


@pytest.fixture
def empty_cast(quill_data_dir: Path, monkeypatch, wx_app, quiet_cast_startup, close_cast):
    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    said: list[str] = []
    monkeypatch.setattr(PodcastsAppFrame, "_announce", lambda self, m, *a, **kw: said.append(m))
    frame = PodcastsAppFrame()
    frame.said = said
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        try:
            assert close_cast(frame, loop=loop)
        finally:
            wx.EventLoop.SetActive(previous_loop)


def test_building_the_window_says_nothing_and_the_arrival_waits_for_it(
    empty_cast, later, monkeypatch
) -> None:
    frame = empty_cast
    assert frame._current_place == "podcasts"
    assert not any(str(m).startswith("No podcasts yet") for m in frame.said)
    monkeypatch.setattr(frame.frame, "IsActive", lambda: True)
    frame.frame.Show()
    try:
        from quill.ui.podcasts.launch_first_task import say_landing_place

        say_landing_place(frame)
    finally:
        frame.frame.Hide()
    from quill.core.podcasts import places as places_model

    expected = places_model.empty_state(frame._podcast_library, "podcasts")
    assert [m for m in frame.said if str(m).startswith("No podcasts yet")] == [expected]
