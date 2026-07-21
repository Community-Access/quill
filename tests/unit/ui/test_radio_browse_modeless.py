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
from quill.ui.radio.favorites_manager_dialog import FavoritesManagerDialog
from quill.ui.radio.schedule_recording_dialog import ScheduleRecordingDialog
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


def _make_favorites(windows: object | None) -> FavoritesManagerDialog:
    controller = SimpleNamespace(state=SimpleNamespace(volume_percent=100, muted=False))
    return FavoritesManagerDialog(
        None,
        favorites=RadioFavoritesStore(),
        controller=controller,
        announce_cb=lambda _m: None,
        windows=windows,
    )


def test_modeless_favorites_is_a_frame_with_window_menu(_app: wx.App) -> None:
    dlg = _make_favorites(WindowManager(wx))
    try:
        assert isinstance(dlg._win, wx.Frame)
        bar = dlg._win.GetMenuBar()
        assert bar is not None
        titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
        assert "Window" in titles
        # self.dialog aliases the top-level window so child dialogs parent right.
        assert dlg.dialog is dlg._win
    finally:
        dlg._win.Destroy()


def test_modal_favorites_stays_a_dialog(_app: wx.App) -> None:
    dlg = _make_favorites(None)
    try:
        assert isinstance(dlg._win, wx.Dialog)
        assert dlg.dialog is dlg._win
    finally:
        dlg._win.Destroy()


def _make_schedule(windows: object | None) -> ScheduleRecordingDialog:
    return ScheduleRecordingDialog(
        None,
        entries=[],
        on_add=lambda _e: None,
        on_remove=lambda _id: True,
        announce_cb=lambda _m: None,
        windows=windows,
    )


def test_modeless_schedule_is_a_frame_with_window_menu(_app: wx.App) -> None:
    dlg = _make_schedule(WindowManager(wx))
    try:
        assert isinstance(dlg._win, wx.Frame)
        bar = dlg._win.GetMenuBar()
        titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
        assert "Window" in titles
    finally:
        dlg._win.Destroy()


def test_modal_schedule_stays_a_dialog(_app: wx.App) -> None:
    dlg = _make_schedule(None)
    try:
        assert isinstance(dlg._win, wx.Dialog)
    finally:
        dlg._win.Destroy()


def _make_weather(windows: object | None, tmp_path):  # type: ignore[no-untyped-def]
    from quill.ui.weather.weather_center_dialog import WeatherCenterDialog

    return WeatherCenterDialog(
        None,
        data_dir=tmp_path,
        task_manager=SimpleNamespace(),
        safe_mode=True,
        announce_cb=lambda _m: None,
        windows=windows,
    )


def test_modeless_weather_is_a_frame_with_window_menu(_app: wx.App, tmp_path) -> None:
    dlg = _make_weather(WindowManager(wx), tmp_path)
    try:
        assert isinstance(dlg._win, wx.Frame)
        bar = dlg._win.GetMenuBar()
        titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
        assert "Window" in titles
        assert dlg.dialog is dlg._win  # child dialogs parent to the top-level window
    finally:
        dlg._win.Destroy()


def test_modal_weather_stays_a_dialog(_app: wx.App, tmp_path) -> None:
    dlg = _make_weather(None, tmp_path)
    try:
        assert isinstance(dlg._win, wx.Dialog)
    finally:
        dlg._win.Destroy()
