"""Standalone Quill Weather tray app: construction/wiring smoke, the
close-to-tray path (so a closed window keeps the alert watch alive), the tray
menu, and first-run monitoring defaults. Uses a real wx.App but never shows a
window or enters a modal."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.apps.weather import WeatherAppFrame
from quill.core.weather import locations as loc_store
from quill.core.weather import monitor
from quill.core.weather.models import WeatherLocation


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    a.Destroy()


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    # conftest sets _DEV_BUILD=True, so QUILL_DATA_DIR is honored for isolation.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    return tmp_path


def _close_event() -> tuple[SimpleNamespace, dict]:
    flags: dict = {"vetoed": False, "skipped": False}
    event = SimpleNamespace(
        Veto=lambda: flags.__setitem__("vetoed", True),
        Skip=lambda: flags.__setitem__("skipped", True),
    )
    return event, flags


def test_weather_app_builds_with_expected_menus(app, data_dir) -> None:
    frame = WeatherAppFrame(safe_mode=True)  # Safe Mode: no network at startup
    try:
        bar = frame.frame.GetMenuBar()
        titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
        assert "File" in titles
        assert "Weather" in titles
        assert "Options" in titles
        assert "Help" in titles
        # The shared Weather menu brought the monitoring toggle with it.
        weather_menu = bar.GetMenu(titles.index("Weather"))
        labels = [
            weather_menu.FindItemByPosition(i).GetItemLabelText()
            for i in range(weather_menu.GetMenuItemCount())
            if weather_menu.FindItemByPosition(i).GetKind() != wx.ITEM_SEPARATOR
        ]
        assert any("Monitoring" in text for text in labels)
    finally:
        frame.frame.Destroy()


def test_close_minimizes_to_tray_by_default(app, data_dir) -> None:
    frame = WeatherAppFrame(safe_mode=True)
    try:
        hidden: list[bool] = []
        frame.frame.Hide = lambda: hidden.append(True)  # type: ignore[method-assign]
        event, flags = _close_event()
        frame._on_weather_app_close(event)
        assert flags["vetoed"] is True  # close was intercepted...
        assert hidden == [True]  # ...and the window went to the tray
        assert flags["skipped"] is False  # not a real close
    finally:
        frame.frame.Destroy()


def test_explicit_exit_really_closes(app, data_dir) -> None:
    frame = WeatherAppFrame(safe_mode=True)
    try:
        # An explicit Exit sets _exit_requested; the close then runs shutdown+Skip
        # instead of minimizing, even though close_to_tray is the default.
        frame._exit_requested = True
        shut: list[bool] = []
        frame._weather_app_shutdown = lambda: shut.append(True)  # type: ignore[method-assign]
        event, flags = _close_event()
        frame._on_weather_app_close(event)
        assert shut == [True]
        assert flags["skipped"] is True
        assert flags["vetoed"] is False
    finally:
        frame.frame.Destroy()


def test_close_to_tray_off_exits(app, data_dir) -> None:
    from quill.core.weather import settings as settings_mod

    settings = settings_mod.load_settings(data_dir)
    settings.app_close_to_tray = False
    settings_mod.save_settings(data_dir, settings)

    frame = WeatherAppFrame(safe_mode=True)
    try:
        shut: list[bool] = []
        frame._weather_app_shutdown = lambda: shut.append(True)  # type: ignore[method-assign]
        event, flags = _close_event()
        frame._on_weather_app_close(event)
        assert shut == [True]  # closes for real when the pref is off
        assert flags["skipped"] is True
    finally:
        frame.frame.Destroy()


def test_tray_menu_reflects_monitoring_state(app, data_dir) -> None:
    frame = WeatherAppFrame(safe_mode=True)
    try:
        menu = wx.Menu()
        frame._build_weather_tray_menu(menu)
        labels = [
            menu.FindItemByPosition(i).GetItemLabelText() for i in range(menu.GetMenuItemCount())
        ]
        assert any("Monitoring: off" in t for t in labels)  # not started in Safe Mode
        assert any("Open Weather Center" in t for t in labels)
        assert any("Start Monitoring" in t for t in labels)
    finally:
        frame.frame.Destroy()


def test_startup_monitoring_first_run_enables_for_primary(app, data_dir, monkeypatch) -> None:
    # A saved location but no monitor config yet == first run -> default on.
    store = loc_store.WeatherLocationStore()
    store.add(WeatherLocation(display_name="Tucson, AZ", latitude=32.22, longitude=-110.97))
    loc_store.save_locations(data_dir, store)

    frame = WeatherAppFrame(safe_mode=False)
    try:
        started: list[bool] = []
        frame.start_weather_monitoring = lambda **_k: started.append(True)  # type: ignore[method-assign]
        assert monitor.config_exists(data_dir) is False  # nothing configured yet
        frame._weather_app_startup_monitoring()
        assert started == [True]  # first run defaults monitoring on
    finally:
        frame.frame.Destroy()


def test_startup_monitoring_respects_user_disabled(app, data_dir) -> None:
    # A location exists, but the user explicitly turned monitoring off.
    store = loc_store.WeatherLocationStore()
    store.add(WeatherLocation(display_name="Tucson, AZ", latitude=32.22, longitude=-110.97))
    loc_store.save_locations(data_dir, store)
    monitor.save_config(data_dir, monitor.MonitorConfig(enabled=False, location_id="loc_1"))

    frame = WeatherAppFrame(safe_mode=False)
    try:
        started: list[bool] = []
        frame.start_weather_monitoring = lambda **_k: started.append(True)  # type: ignore[method-assign]
        frame._weather_app_startup_monitoring()
        assert started == []  # respects the user's off choice
    finally:
        frame.frame.Destroy()


def test_check_once_arg_runs_headless_and_skips_gui(monkeypatch) -> None:
    # `quill-weather --check-once` must never build a wx.App/frame -- it is the
    # short-lived, no-window path the Scheduled Task launches.
    import quill.apps.weather as weather_app

    ran: list[bool] = []
    monkeypatch.setattr(weather_app, "_run_headless_check", lambda: ran.append(True) or 0)
    monkeypatch.setattr(weather_app.sys, "argv", ["quill-weather", "--check-once"])

    def _boom(*_a, **_k):
        raise AssertionError("the GUI must not start in --check-once mode")

    monkeypatch.setattr(weather_app.wx, "App", _boom)
    assert weather_app.main() == 0
    assert ran == [True]


def test_headless_check_toasts_only_new_alerts(data_dir, monkeypatch) -> None:
    import quill.apps.weather as weather_app
    from quill.core.weather import headless_check
    from quill.core.weather.models import WeatherAlert

    store = loc_store.WeatherLocationStore()
    store.add(WeatherLocation(display_name="Tucson, AZ", latitude=32.22, longitude=-110.97))
    loc_store.save_locations(data_dir, store)
    # Baseline already recorded, so the alert below is "new".
    monitor.save_notified_ids(data_dir, set())

    monkeypatch.setattr(
        headless_check,
        "run_check",
        lambda *_a, **_k: headless_check.HeadlessCheckResult(
            new_alerts=[WeatherAlert(id="t", event="Tornado Warning", severity="Extreme")],
            checked=True,
        ),
    )
    toasts: list[tuple[str, str]] = []
    monkeypatch.setattr(weather_app, "_show_alert_toast", lambda t, b: toasts.append((t, b)))
    assert weather_app._run_headless_check() == 0
    assert toasts and "Tornado Warning" in toasts[0][0]


def test_background_toggle_registers_scheduled_task(app, data_dir, monkeypatch) -> None:
    from quill.platform.windows import scheduled_task

    calls: list[str] = []
    monkeypatch.setattr(scheduled_task, "is_windows", lambda: True)
    monkeypatch.setattr(scheduled_task, "register", lambda mins: calls.append(f"register:{mins}"))
    monkeypatch.setattr(scheduled_task, "unregister", lambda: calls.append("unregister"))
    # First is_registered() is for the menu-build; then reflect after toggling.
    states = iter([False, True, True])
    monkeypatch.setattr(scheduled_task, "is_registered", lambda: next(states, True))

    monitor.save_config(data_dir, monitor.MonitorConfig(interval_minutes=12))
    frame = WeatherAppFrame(safe_mode=True)
    try:
        frame._set_background_check(True)
        assert calls == ["register:12"]  # registered at the monitor cadence
    finally:
        frame.frame.Destroy()
