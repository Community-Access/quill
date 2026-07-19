"""Headless build + wiring smoke for the QUILL Weather dialogs, plus the pure
list/detail formatting helpers. Uses a real wx.App so construction and the
report-rendering path are exercised, but never shows a modal."""

from __future__ import annotations

import pytest
import wx

from quill.core.weather.models import (
    CurrentConditions,
    ForecastPeriod,
    WeatherAlert,
    WeatherLocation,
    WeatherReport,
)
from quill.core.weather.settings import WeatherSettings
from quill.ui.weather import weather_center_dialog as wcd
from quill.ui.weather.add_location_dialog import AddLocationDialog
from quill.ui.weather.settings_dialog import WeatherSettingsDialog
from quill.ui.weather.weather_center_dialog import WeatherCenterDialog


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    a.Destroy()


class _FakeTaskManager:
    def submit(self, _name, _work, *, on_success=None, on_failure=None):
        return None  # never actually run work in the build smoke


# -- pure helpers -------------------------------------------------------------


def test_alert_list_label() -> None:
    alert = WeatherAlert(
        "i", "Tornado Warning", "Extreme", "Immediate", area_description="Pima, AZ; Pinal, AZ"
    )
    assert wcd._alert_list_label(alert) == "Tornado Warning -- Pima, AZ -- Critical"


def test_period_detail_text_leads_with_day_and_temp() -> None:
    p = ForecastPeriod(
        "This Afternoon", 96, "F", "Hot", detailed_forecast="Very hot, high near 96."
    )
    text = wcd._period_detail_text(p)
    assert text.startswith("This Afternoon: 96 deg F")  # day + temp at the top
    assert "Very hot, high near 96." in text  # then the full detail, copyable


def test_weather_center_has_labels_before_each_readonly_field(app, tmp_path) -> None:
    # A StaticText immediately before each read-only field is what names it for
    # a screen reader; every detail field must have one.
    dlg = WeatherCenterDialog(
        None, data_dir=tmp_path, task_manager=_FakeTaskManager(), safe_mode=False
    )
    assert dlg._alert_detail_label.GetLabelText()
    assert dlg._period_detail_label.GetLabelText()
    dlg.dialog.Destroy()


def test_alert_detail_text_includes_instructions() -> None:
    alert = WeatherAlert(
        "i",
        "Flash Flood Warning",
        "Severe",
        "Immediate",
        "Observed",
        headline="Flash Flood Warning until 6:30 PM",
        instruction="Move to higher ground now.",
        description="Heavy rain.",
        area_description="Maricopa",
        expires="2026-07-19T18:30:00-07:00",
        sender_name="NWS Phoenix",
    )
    text = wcd._alert_detail_text(alert)
    assert "Flash Flood Warning until 6:30 PM" in text
    assert "Instructions: Move to higher ground now." in text
    assert "Severity Severe" in text
    assert "Issued by NWS Phoenix." in text


# -- dialog construction ------------------------------------------------------


def test_weather_center_builds_and_renders(app, tmp_path) -> None:
    dlg = WeatherCenterDialog(
        None, data_dir=tmp_path, task_manager=_FakeTaskManager(), safe_mode=False
    )
    report = WeatherReport(
        location=WeatherLocation("Home", 32.2, -110.9, resolved_name="Tucson, AZ"),
        current=CurrentConditions(
            text_description="Clear", temperature_f=96.0, wind_speed_mph=5.0, wind_direction="WNW"
        ),
        periods=[
            ForecastPeriod("This Afternoon", 96, "F", "Hot", detailed_forecast="Very hot."),
            ForecastPeriod("Tonight", 71, "F", "Clear", is_daytime=False),
        ],
        alerts=[
            WeatherAlert(
                "a", "Excessive Heat Warning", "Severe", "Expected", instruction="Drink water."
            )
        ],
        office="TWC",
    )
    dlg._render_report(report.location, report)
    assert dlg._alerts_list.GetCount() == 1
    assert "Excessive Heat Warning" in dlg._alerts_list.GetString(0)
    assert "96 degrees Fahrenheit" in dlg._current.GetValue()
    assert dlg._forecast_list.GetCount() == 2
    assert "This Afternoon" in dlg._forecast_list.GetString(0)
    assert "TWC" in dlg._status.GetValue()
    dlg.dialog.Destroy()


def test_weather_center_no_alerts_shows_placeholder(app, tmp_path) -> None:
    dlg = WeatherCenterDialog(
        None, data_dir=tmp_path, task_manager=_FakeTaskManager(), safe_mode=False
    )
    report = WeatherReport(location=WeatherLocation("Home", 1, 2), office="TWC")
    dlg._render_report(report.location, report)
    assert dlg._alerts_list.GetString(0) == "No active alerts."
    dlg.dialog.Destroy()


def test_add_location_dialog_builds(app, tmp_path) -> None:
    from quill.core.weather.locations import WeatherLocationStore

    dlg = AddLocationDialog(
        None,
        store=WeatherLocationStore(),
        data_dir=tmp_path,
        task_manager=_FakeTaskManager(),
        safe_mode=False,
    )
    assert dlg.dialog is not None
    dlg.dialog.Destroy()


def test_add_location_show_applies_modal_ids(app, tmp_path, monkeypatch) -> None:
    # Regression: show() must call apply_modal_ids with valid kwargs
    # (affirmative_id, not ok_id) -- the old ok_id= raised TypeError so the
    # dialog never appeared.
    import quill.ui.dialog_contract as dc
    from quill.core.weather.locations import WeatherLocationStore

    monkeypatch.setattr(dc, "show_modal_dialog", lambda *a, **k: None)
    dlg = AddLocationDialog(
        None,
        store=WeatherLocationStore(),
        data_dir=tmp_path,
        task_manager=_FakeTaskManager(),
        safe_mode=False,
    )
    assert dlg.show() is False  # no exception; nothing added


def test_settings_show_applies_modal_ids(app, tmp_path, monkeypatch) -> None:
    import quill.ui.dialog_contract as dc

    monkeypatch.setattr(dc, "show_modal_dialog", lambda *a, **k: None)
    dlg = WeatherSettingsDialog(None, settings=WeatherSettings(), data_dir=tmp_path)
    assert dlg.show() is False  # no exception


def test_weather_center_show_applies_modal_ids(app, tmp_path, monkeypatch) -> None:
    import quill.ui.dialog_contract as dc

    monkeypatch.setattr(dc, "show_modal_dialog", lambda *a, **k: None)
    dlg = WeatherCenterDialog(
        None, data_dir=tmp_path, task_manager=_FakeTaskManager(), safe_mode=False
    )
    dlg.show()  # no exception (no locations -> no fetch)


class _MenuHost:
    def __init__(self, frame, wx_mod) -> None:
        self.frame = frame
        self._wx = wx_mod
        self._safe_mode = False
        self._task_manager = _FakeTaskManager()

    def _announce(self, _m) -> None:
        pass

    def _show_message_box(self, *_a) -> None:
        pass


def test_weather_menu_appends_with_expected_items(app) -> None:
    from quill.ui.main_frame_weather import WeatherMixin

    class _Host(WeatherMixin, _MenuHost):
        pass

    frame = wx.Frame(None)
    bar = wx.MenuBar()
    _Host(frame, wx)._append_weather_menu(bar)
    titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
    assert "Weather" in titles
    menu = bar.GetMenu(titles.index("Weather"))
    labels = [
        menu.FindItemByPosition(i).GetItemLabelText()
        for i in range(menu.GetMenuItemCount())
        if menu.FindItemByPosition(i).GetKind() != wx.ITEM_SEPARATOR
    ]
    assert any("Weather Now" in text for text in labels)
    assert any("Quick Weather" in text for text in labels)
    assert any("Active Alerts" in text for text in labels)
    assert any("Add Location" in text for text in labels)
    assert any("Settings" in text for text in labels)
    frame.Destroy()


def test_settings_dialog_builds_and_saves(app, tmp_path) -> None:
    from quill.core.weather import settings as settings_mod

    dlg = WeatherSettingsDialog(
        None, settings=WeatherSettings(temperature_unit="F"), data_dir=tmp_path
    )
    dlg._temp.SetSelection(1)  # Celsius
    dlg._q_humidity.SetValue(True)
    dlg._save()
    saved = settings_mod.load_settings(tmp_path)
    assert saved.temperature_unit == "C"
    assert saved.quick_include_humidity is True
    dlg.dialog.Destroy()
