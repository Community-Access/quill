"""Quill Weather before the first place (FUX-09).

The window spoke "Add a weather location to begin monitoring." while it was
being built and named no key and no dependency. A Getting started line now
says it, with the live key and "over the internet", and takes launch focus;
the first place hides it. Weather Center's empty status names its own key.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def weather(tmp_path, monkeypatch, wx_session_app):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    from quill.apps.weather import WeatherAppFrame

    frame = WeatherAppFrame(safe_mode=True)  # Safe Mode: no network at startup
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    try:
        yield frame
    finally:
        WeatherAppFrame._weather_app_shutdown(frame)
        if frame.frame:
            frame.frame.Destroy()


def test_no_place_yet_names_add_location_its_key_and_the_internet(weather) -> None:
    line = weather._first_task_line
    assert line.shown
    assert line.text == (
        "No weather location yet. Add Location (Ctrl+Alt+Shift+L) finds a US place by "
        "ZIP code, city or address, over the internet."
    )


def test_launch_focus_is_the_line_then_open_weather_center(weather, monkeypatch) -> None:
    from quill.core.weather import locations as loc_store
    from quill.core.weather.models import WeatherLocation

    focused: list[str] = []
    monkeypatch.setattr(weather._first_task_line.ctrl, "SetFocus", lambda: focused.append("line"))
    monkeypatch.setattr(weather._open_center_btn, "SetFocus", lambda: focused.append("center"))
    weather._focus_initial_control()
    store = loc_store.load_locations(weather._weather_data_dir())
    store.add(WeatherLocation(display_name="Tucson", latitude=32.2, longitude=-110.9))
    loc_store.save_locations(weather._weather_data_dir(), store)
    weather._refresh_statusbar()
    assert not weather._first_task_line.shown
    weather._focus_initial_control()
    assert focused == ["line", "center"]


def test_weather_center_names_its_own_add_location_key() -> None:
    from quill.ui.weather.center_text import NO_LOCATIONS

    assert NO_LOCATIONS == (
        "No weather location yet. Add Location (Alt+A) finds a US place by ZIP code, "
        "city or address, over the internet."
    )


def test_the_window_coming_back_looks_again(weather, wx_call_after) -> None:
    """A place added in Add Location or Weather Center hides the line when the
    window is in front again, without waiting for a monitoring change."""
    from quill.apps import weather_first_task

    calls = wx_call_after(lambda fn, *a: None)
    weather_first_task._on_activate(weather, wx.ActivateEvent(wx.wxEVT_ACTIVATE, True))
    assert [fn for fn, _args, _kw in calls.calls] == [weather_first_task.refresh]


def test_from_the_tray_with_no_place_the_line_is_said(weather, monkeypatch) -> None:
    from quill.apps import weather_first_task

    monkeypatch.setattr(weather.frame, "IsShown", lambda: False)
    weather_first_task.say_if_hidden(weather)
    assert weather.said == [weather_first_task.line_text(weather)]
