"""The main window's swappable middle (main_view_host, main_view_menu).

The pure choice is pinned in tests/unit/core/radio/test_main_view.py. What is
here is the part that can strand somebody:

* **the main window is never empty.** A surface that will not build leaves the
  window on whatever it was showing and says so -- an empty main window is the
  one state a listener cannot get out of by keyboard;
* **built once, kept.** Switching back shows the page you left, with its tree
  still expanded, rather than a freshly rebuilt one;
* **a menu item whose surface is the main view goes there**, instead of
  stacking a second copy on top of the one already in front of you. That was
  the original report;
* **the stored setting follows what is actually on screen.** A checkmark on a
  view that failed to build is a menu lying about where you are.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.radio import main_view

wx = pytest.importorskip("wx")

from quill.ui.radio import main_view_menu  # noqa: E402
from quill.ui.radio.main_view_host import MainViewHost  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Surface:
    """A stand-in for Browse/Search/Recordings/the Player."""

    def __init__(self, page: Any) -> None:
        self.page = page
        self.focused = 0

    def focus_default_control(self) -> None:
        self.focused += 1


class _App:
    """Just enough of the app for the host to drive."""

    def __init__(self, frame: Any, *, broken: tuple[str, ...] = ()) -> None:
        self.frame = frame
        self.said: list[str] = []
        self.built: list[str] = []
        self._broken = broken
        self.surfaces: dict[str, _Surface] = {}
        self._favorites_tree = wx.TreeCtrl(frame)

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _make(self, view_id: str, page: Any) -> Any:
        self.built.append(view_id)
        if view_id in self._broken:
            raise RuntimeError("no such thing here")
        surface = _Surface(page)
        self.surfaces[view_id] = surface
        return surface

    def open_browse_stations(self, *, embed_in: Any = None) -> Any:
        return self._make("browse", embed_in)

    def open_internet_radio(self, *, embed_in: Any = None) -> Any:
        return self._make("search", embed_in)

    def open_radio_recordings(self, *, embed_in: Any = None) -> Any:
        return self._make("recordings", embed_in)

    def _radio_go_to_player(self, *, embed_in: Any = None) -> Any:
        return self._make("player", embed_in)


@pytest.fixture
def host():
    frame = wx.Frame(None)
    panel = wx.Panel(frame)
    app = _App(frame)
    view_host = MainViewHost(app, wx)
    favorites_page = wx.Panel(panel)
    view_host.build(panel, favorites_page)
    app._main_view_host = view_host
    yield app, view_host
    frame.Destroy()


def test_it_opens_on_the_favorites_tree(host) -> None:
    _app, view_host = host

    assert view_host.current == main_view.FAVORITES


def test_switching_builds_the_surface_once_and_keeps_it(host) -> None:
    """Rebuilding would throw away the tree somebody spent time expanding."""
    app, view_host = host

    view_host.show("browse", focus=False)
    view_host.show(main_view.FAVORITES, focus=False)
    view_host.show("browse", focus=False)

    assert app.built == ["browse"], "built once, not on every visit"
    assert view_host.current == "browse"


def test_the_surface_is_built_into_a_page_not_a_window_of_its_own(host) -> None:
    app, view_host = host

    view_host.show("browse", focus=False)

    assert app.surfaces["browse"].page is not None
    assert app.surfaces["browse"].page.GetTopLevelParent() is app.frame


def test_switching_says_which_view_and_what_it_is(host) -> None:
    app, view_host = host

    view_host.show("recordings", focus=False)

    assert "Radio Recordings" in app.said[-1]


def test_focus_lands_on_the_surfaces_own_default_control(host) -> None:
    app, view_host = host

    view_host.show("search", announce=False, focus=False)
    view_host.focus_current()

    assert app.surfaces["search"].focused == 1


def test_a_surface_that_will_not_build_leaves_the_window_where_it_was() -> None:
    """An empty main window is the one state you cannot leave by keyboard."""
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        app = _App(frame, broken=("player",))
        view_host = MainViewHost(app, wx)
        view_host.build(panel, wx.Panel(panel))

        shown = view_host.show("player", focus=False)

        assert shown == main_view.FAVORITES
        assert view_host.current == main_view.FAVORITES
        assert "could not be shown" in app.said[-1]
        assert "Favorite stations" in app.said[-1]
    finally:
        frame.Destroy()


# -- the menu --------------------------------------------------------------------


class _MenuApp(_App):
    """The app plus the history object main_view_menu writes through."""

    def __init__(self, frame: Any, **kwargs: Any) -> None:
        super().__init__(frame, **kwargs)
        from quill.core.radio.history import RadioHistory

        self._radio_history = RadioHistory()


@pytest.fixture
def menu_host(tmp_path, monkeypatch):
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    frame = wx.Frame(None)
    panel = wx.Panel(frame)
    app = _MenuApp(frame)
    view_host = MainViewHost(app, wx)
    view_host.build(panel, wx.Panel(panel))
    app._main_view_host = view_host
    menu = wx.Menu()
    main_view_menu.append(app, menu, wx)
    yield app, view_host
    frame.Destroy()


def test_every_view_item_advertises_a_key(menu_host) -> None:
    """The house rule: an enabled menu item shows its keyboard route."""
    assert len(main_view_menu.KEYS) == len(main_view.MAIN_VIEWS)
    assert len(set(main_view_menu.KEYS)) == len(main_view_menu.KEYS)


def test_choosing_a_view_switches_and_remembers_it(menu_host) -> None:
    app, view_host = menu_host

    main_view_menu.switch(app, "browse")

    assert view_host.current == "browse"
    assert app._radio_history.main_view == "browse"


def test_choosing_the_view_you_are_already_on_takes_focus_there(menu_host) -> None:
    """Pressing it twice is somebody trying to get back to the list."""
    app, view_host = menu_host
    main_view_menu.switch(app, "browse")
    built_before = list(app.built)

    main_view_menu.switch(app, "browse")

    assert app.built == built_before, "no second copy"
    assert app.surfaces["browse"].focused >= 1


def test_a_view_that_fails_stores_the_one_actually_showing(tmp_path, monkeypatch) -> None:
    """A checkmark on a view that failed to build is a menu lying about where you are."""
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        app = _MenuApp(frame, broken=("player",))
        view_host = MainViewHost(app, wx)
        view_host.build(panel, wx.Panel(panel))
        app._main_view_host = view_host
        main_view_menu.append(app, wx.Menu(), wx)

        main_view_menu.switch(app, "player")

        assert view_host.current == main_view.FAVORITES
        assert app._radio_history.main_view == main_view.FAVORITES
    finally:
        frame.Destroy()
