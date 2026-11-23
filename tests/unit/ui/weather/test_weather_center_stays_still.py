"""The Weather Center's lists keep the reader's row through a refresh (FUX-06).

Every fetch used to Set() all four lists -- selection gone, list back at the
top -- and forced each details box to the first row. A slow answer for the
place chosen before could replace the one just chosen.
"""

from __future__ import annotations

import pytest

from quill.core.weather.models import (
    ForecastPeriod,
    WeatherAlert,
    WeatherLocation,
    WeatherReport,
)
from quill.ui.weather.weather_center_dialog import WeatherCenterDialog
from tests.wx_session import shared_wx_app


class _Tasks:
    def __init__(self) -> None:
        self.submitted: list = []

    def submit(self, _name, _work, *, on_success=None, on_failure=None):
        self.submitted.append(on_success)


@pytest.fixture
def center(tmp_path):
    shared_wx_app()
    said: list[str] = []
    tasks = _Tasks()
    dlg = WeatherCenterDialog(
        None, data_dir=tmp_path, task_manager=tasks, safe_mode=False, announce_cb=said.append
    )
    dlg.said = said
    dlg.tasks = tasks
    yield dlg
    dlg.dialog.Destroy()


def _report(periods: list[str], alerts: list[str], name: str = "Home") -> WeatherReport:
    return WeatherReport(
        location=WeatherLocation(name, 32.2, -110.9),
        periods=[
            ForecastPeriod(p, 80, "F", f"{p} sky", detailed_forecast=f"{p} detail") for p in periods
        ],
        alerts=[WeatherAlert(a, f"{a} Warning", "Severe", "Expected") for a in alerts],
        office="TWC",
    )


def test_a_refresh_keeps_the_forecast_period_the_reader_is_on(center) -> None:
    report = _report(["Today", "Tonight", "Monday"], [])
    center._render_report(report.location, report)
    center._forecast_list.SetSelection(1)  # Tonight
    later = _report(["Tonight", "Monday", "Monday Night"], [])  # "Today" has passed
    center._render_report(later.location, later)
    assert center._forecast_list.GetStringSelection().startswith("Tonight")
    assert "Tonight detail" in center._period_detail.GetValue()


def test_an_alert_that_has_gone_is_said_once_and_its_neighbour_chosen(center, monkeypatch) -> None:
    import wx

    queued: list = []
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: queued.append(fn))
    report = _report(["Today"], ["Flood", "Heat"])
    center._render_report(report.location, report)
    center._alerts_list.SetSelection(0)  # Flood
    later = _report(["Today"], ["Heat"])
    center._render_report(later.location, later)
    assert center._alerts_list.GetStringSelection().startswith("Heat")
    assert not center.said[-1].endswith("no longer in the list."), "not over the row change"
    queued.pop()()  # once the screen reader has read the alert the reader is on
    assert center.said[-1].endswith("The Flood Warning is no longer in the list.")


def test_another_place_is_not_an_expiry(center, monkeypatch) -> None:
    import wx

    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: fn(*a))
    report = _report(["Today"], ["Flood"])
    center._render_report(report.location, report)
    center._alerts_list.SetSelection(0)
    away = WeatherLocation("Cabin", 40.0, -105.0)
    other = _report(["Today"], ["Wind"], name="Cabin")
    center._render_report(away, other)
    assert not any("no longer in the list" in text for text in center.said)


def test_the_gone_sentence_is_said_even_with_the_summary_off(center, monkeypatch) -> None:
    import wx

    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: fn(*a))
    center._settings.announce_alert_count_on_open = False
    report = _report(["Today"], ["Flood", "Heat"])
    center._render_report(report.location, report)
    center._alerts_list.SetSelection(0)
    later = _report(["Today"], ["Heat"])
    center._render_report(later.location, later)
    assert center.said == ["The Flood Warning is no longer in the list."]


def test_a_redraw_with_nothing_new_does_not_say_the_summary_again(center) -> None:
    report = _report(["Today"], ["Heat"])
    center._render_report(report.location, report)
    count = len(center.said)
    center._render_report(report.location, report, fetched=False)  # after Settings
    assert len(center.said) == count


def test_a_slow_answer_for_the_place_chosen_before_is_dropped(center, wx_call_after) -> None:
    for name in ("Home", "Cabin"):
        center._store.add(WeatherLocation(name, 32.2, -110.9))
    center._reload_location_choice()
    wx_call_after()  # CallAfter runs at once
    center._location_choice.SetSelection(0)
    center._refresh()
    center._location_choice.SetSelection(1)
    center._refresh()
    newer, older = center.tasks.submitted[-1], center.tasks.submitted[-2]
    newer("op", _report(["Today"], [], name="Cabin"))
    older("op", _report(["Today"], [], name="Home"))  # arrives last, is out of date
    assert center._current.GetValue().startswith("Weather for Cabin.")
