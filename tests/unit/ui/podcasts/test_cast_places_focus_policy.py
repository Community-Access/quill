"""Places and content arrows never move focus between the two surfaces."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.place_content import CastPlaceContentMixin
from quill.ui.podcasts.places_host import CastPlacesHostMixin
from quill.ui.podcasts.places_list import PlacesList
from tests.wx_session import shared_wx_app


@pytest.fixture
def wx_app():
    app = wx.GetApp() or shared_wx_app()
    yield app


class _KeyEvent:
    def __init__(self, code: int) -> None:
        self.code = code
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self.code

    def ControlDown(self) -> bool:
        return False

    def Skip(self, _skip: bool = True) -> None:
        self.skipped = True


class _Host:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []

    def show_place(self, place_id: str, *, focus: bool = True) -> None:
        self.calls.append((place_id, focus))


@pytest.mark.parametrize("key", [wx.WXK_RETURN, wx.WXK_RIGHT])
def test_entering_a_place_updates_content_without_stealing_focus(wx_app, key: int) -> None:
    frame = wx.Frame(None)
    panel = wx.Panel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    host = _Host()
    places = PlacesList(
        panel,
        wx=wx,
        on_enter=lambda place_id: CastPlacesHostMixin._on_place_entered(host, place_id),
        on_change=lambda place_id: CastPlacesHostMixin._on_place_changed(host, place_id),
        on_hide=lambda _place_id: None,
        on_rename=lambda _place_id: None,
        on_menu=lambda _place_id: None,
    )
    sizer.Add(places.label, 0)
    sizer.Add(places.box, 1, wx.EXPAND)
    panel.SetSizer(sizer)
    frame.SetSize((400, 240))
    frame.Show()
    places.set_rows([("inbox", "Inbox"), ("podcasts", "Podcasts")], keep="podcasts")
    places.box.SetFocus()
    wx.Yield()

    try:
        places._on_key(_KeyEvent(key))

        assert host.calls == [("podcasts", False)]
        assert wx.Window.FindFocus() is places.box
    finally:
        frame.Destroy()
        wx.Yield()


@pytest.mark.parametrize("key", [wx.WXK_UP, wx.WXK_LEFT, wx.WXK_BACK])
def test_content_list_navigation_does_not_focus_places(wx_app, key: int) -> None:
    focused: list[bool] = []
    host: Any = SimpleNamespace(
        _list_selected_data=lambda: ("episode", "show\x00episode"),
        _episodes=SimpleNamespace(GetFirstSelected=lambda: 0),
        _places=SimpleNamespace(focus=lambda: focused.append(True)),
        _back_from_show_in_place=lambda: False,
    )
    event = _KeyEvent(key)

    CastPlacesHostMixin._on_content_list_key(host, event)

    assert event.skipped
    assert focused == []


def _loading_host():
    calls = []
    initial_focus = object()
    current_focus = [initial_focus]
    host = SimpleNamespace(
        _current_place="downloads",
        _podcast_library=PodcastLibrary(),
        _wx=SimpleNamespace(Window=SimpleNamespace(FindFocus=lambda: current_focus[0])),
        _content=SimpleNamespace(
            TREE="tree",
            LIST="list",
            show=lambda page: calls.append(("show", page)),
            set_heading=lambda text: calls.append(("heading", text)),
            focus=lambda: calls.append(("focus",)),
        ),
    )
    return host, calls, initial_focus, current_focus


@pytest.mark.parametrize("focus", [False, True])
def test_large_place_opening_yields_before_heading_and_focus(focus) -> None:
    host, calls, initial_focus, _current_focus = _loading_host()
    chunks = CastPlaceContentMixin._loading_place_chunks(
        host, "downloads", focus=focus, initial_focus=initial_focus
    )
    next(chunks)
    assert calls == [("show", "list")]
    next(chunks)
    assert calls[-1] == ("heading", "Downloads (loading...)")
    list(chunks)
    assert (("focus",) in calls) is focus


def test_large_place_opening_does_not_steal_focus_after_user_movement() -> None:
    host, calls, initial_focus, current_focus = _loading_host()
    chunks = CastPlaceContentMixin._loading_place_chunks(
        host, "downloads", focus=True, initial_focus=initial_focus
    )
    next(chunks)
    current_focus[0] = object()
    list(chunks)
    assert ("focus",) not in calls


def test_switching_places_during_opening_cannot_publish_the_old_heading() -> None:
    host, calls, initial_focus, _current_focus = _loading_host()
    chunks = CastPlaceContentMixin._loading_place_chunks(
        host, "downloads", focus=True, initial_focus=initial_focus
    )
    next(chunks)
    host._current_place = "podcasts"
    list(chunks)
    assert calls == [("show", "list")]


def test_cancelling_large_place_opening_leaves_no_late_heading_or_focus() -> None:
    host, calls, initial_focus, _current_focus = _loading_host()
    chunks = CastPlaceContentMixin._loading_place_chunks(
        host, "downloads", focus=True, initial_focus=initial_focus
    )
    next(chunks)
    chunks.close()
    assert list(chunks) == []
    assert calls == [("show", "list")]
