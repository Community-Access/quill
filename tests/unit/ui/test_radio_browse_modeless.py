"""Browse Stations converts to a modeless frame when given a WindowManager.

The radio window model turns the heavy surfaces from modal dialogs into
modeless frames that carry the persistent menu bar + &Window menu (standalone
Radio), while embedded QUILL -- which passes no WindowManager -- keeps them as
modal dialogs. This checks the top-level object type and the menu bar wiring
without opening or pumping the window.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.core.radio.favorites import RadioFavoritesStore
from quill.ui.radio.browse_tree_dialog import BrowseTreeDialog
from quill.ui.radio.station_browser_dialog import StationBrowserDialog
from quill.ui.window_menu import WindowManager


@pytest.fixture(scope="module")
def _app() -> wx.App:
    return wx.App()


def _make(windows: object | None) -> BrowseTreeDialog:
    controller = SimpleNamespace(state=SimpleNamespace(volume_percent=100, muted=False))
    return BrowseTreeDialog(
        None,
        controller=controller,
        favorites_store=RadioFavoritesStore(),
        task_manager=SimpleNamespace(),
        safe_mode=True,  # no live source fetches during construction
        announce_cb=lambda _m: None,
        windows=windows,
    )


def test_modeless_browse_is_a_frame_with_window_menu(_app: wx.App) -> None:
    manager = WindowManager(wx)
    dlg = _make(manager)
    try:
        assert isinstance(dlg._win, wx.Frame)
        bar = dlg._win.GetMenuBar()
        assert bar is not None
        titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
        assert "Window" in titles  # the shared &Window menu was installed
    finally:
        dlg._win.Destroy()


def test_modal_browse_stays_a_dialog(_app: wx.App) -> None:
    dlg = _make(None)
    try:
        assert isinstance(dlg._win, wx.Dialog)
        assert not isinstance(dlg._win, wx.Frame)  # stays modal, no menu bar
    finally:
        dlg._win.Destroy()


def _make_search(windows: object | None) -> StationBrowserDialog:
    controller = SimpleNamespace(state=SimpleNamespace(volume_percent=100, muted=False))
    return StationBrowserDialog(
        None,
        controller=controller,
        favorites_store=RadioFavoritesStore(),
        task_manager=SimpleNamespace(),
        safe_mode=True,
        announce_cb=lambda _m: None,
        windows=windows,
    )


def test_modeless_search_is_a_frame_with_window_menu(_app: wx.App) -> None:
    dlg = _make_search(WindowManager(wx))
    try:
        assert isinstance(dlg._win, wx.Frame)
        bar = dlg._win.GetMenuBar()
        assert bar is not None
        titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
        assert "Window" in titles
    finally:
        dlg._win.Destroy()


def test_modal_search_stays_a_dialog(_app: wx.App) -> None:
    dlg = _make_search(None)
    try:
        assert isinstance(dlg._win, wx.Dialog)
        assert not isinstance(dlg._win, wx.Frame)
    finally:
        dlg._win.Destroy()
