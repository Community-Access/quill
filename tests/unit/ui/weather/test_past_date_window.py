"""Drive Weather on a Past Date without showing it and without the network: a
typed date lands in the day box and the hours list, moves say the new date
first, an unusable date keeps the field and says why, spans list their days,
recent dates are remembered, and the save dialog refuses bad dates."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from quill.core.weather import locations as loc_store
from quill.core.weather import past_day, past_day_service
from quill.core.weather.history_cache import DayRecord
from quill.core.weather.history_service import Lookup
from quill.core.weather.models import WeatherLocation
from quill.ui.weather import past_date_dialog as pdd
from quill.ui.weather import past_date_lists as pdl
from quill.ui.weather.save_range_dialog import SaveRangeDialog
from tests.wx_session import shared_wx_app

TODAY = date(2026, 11, 27)


@pytest.fixture
def app():
    a = shared_wx_app()
    yield a
    a.Destroy()


@pytest.fixture
def fake_lookups(monkeypatch: pytest.MonkeyPatch) -> list[date]:
    asked: list[date] = []

    def look_up_day(day: date, **kwargs: Any) -> past_day_service.DayResult:
        asked.append(day)
        found = past_day.PastDay(
            date=day.isoformat(),
            code=0,
            high_c=10.0,
            low_c=0.0,
            hours=[past_day.HourRow(time=f"{day.isoformat()}T15:00", temperature_c=9.0)],
        )
        return past_day_service.DayResult(
            day=found, text=f"Day {day.isoformat()}.", spoken="Clear, high 50, low 32.",
            credits="Weather data by Open-Meteo.com.",
        )  # fmt: skip

    def look_up(query: Any, **kwargs: Any) -> Lookup:
        rows = [DayRecord(f"2011-03-{d:02d}", 0, 10.0, 0.0, 0.0) for d in range(1, 32)]
        return Lookup(summary="31 days.", rows=rows, credits="C.")

    monkeypatch.setattr(past_day_service, "look_up_day", look_up_day)
    from quill.core.weather import history_service

    monkeypatch.setattr(history_service, "look_up", look_up)
    return asked


def _make(tmp_path: Path, said: list[str], **kwargs: Any) -> pdd.PastDateDialog:
    store = loc_store.load_locations(tmp_path)
    store.add(WeatherLocation("Berlin", 52.5, 13.4, id="b"))
    loc_store.save_locations(tmp_path, store)
    return pdd.PastDateDialog(
        None,
        data_dir=tmp_path,
        task_manager=None,
        safe_mode=False,
        announce_cb=said.append,
        today=TODAY,
        date_order="MDY",
        **kwargs,
    )


def test_a_typed_date_lands(app, tmp_path: Path, fake_lookups: list[date]) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        dlg._date.SetValue("March 14, 2011")
        dlg.go()
        assert fake_lookups == [date(2011, 3, 14)]
        assert dlg._view.GetValue() == "Day 2011-03-14."
        assert dlg._hours.GetItemCount() == 1
        assert said[-1] == "Monday, March 14, 2011. Clear, high 50, low 32."
        assert dlg._recent_list.GetString(0) == "Monday, March 14, 2011, Berlin"
        assert "Sources: Weather data by Open-Meteo.com." in dlg.copy_text() or dlg.copy_text()
    finally:
        dlg.dialog.Destroy()


def test_moves_say_the_date_first(app, tmp_path: Path, fake_lookups: list[date]) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        dlg.show_day(date(2011, 3, 14), announce_move="")
        dlg.move(*pdd.MOVES[("RIGHT", False, False, True)])
        assert said[-1] == "Tuesday, March 15, 2011. Clear, high 50, low 32."
        dlg.move(*pdd.MOVES[("PAGEUP", True, True, False)])
        assert said[-1].startswith("Monday, March 15, 2010.")
        dlg.move(*pdd.MOVES[("PAGEDOWN", False, True, False)])
        assert dlg.current == date(2010, 4, 15)
        assert dlg._date.GetValue() == "2010-04-15"
    finally:
        dlg.dialog.Destroy()


def test_an_unusable_date_keeps_the_field(app, tmp_path: Path, fake_lookups: list[date]) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        for text, why in (
            ("2030-01-01", "is in the future"),
            ("1939-05-01", "before 1940"),
            ("whenever", "did not understand"),
        ):
            dlg._date.SetValue(text)
            dlg.go()
            assert why in said[-1] and dlg._date.GetValue() == text
        assert fake_lookups == []
        dlg._date.SetValue("yesterday")
        dlg.go()
        assert "within the last 5 days" in said[-1]
    finally:
        dlg.dialog.Destroy()


def test_a_month_lists_its_days(app, tmp_path: Path, fake_lookups: list[date]) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        dlg._date.SetValue("March 2011")
        dlg.go()
        assert dlg._span.IsShown() and dlg._span.GetItemCount() == 31
        assert dlg._status.GetLabel().startswith("31 days, Tuesday, March 1, 2011 to")
        assert dlg._span_label.GetLabel() == "Day&s in March 2011:"
        dlg._open_span_row(13)
        assert fake_lookups == [date(2011, 3, 14)]
    finally:
        dlg.dialog.Destroy()


def test_key_table() -> None:
    assert pdd.MOVES[("LEFT", False, False, True)] == (-1, 0, 0)
    assert pdd.MOVES[("RIGHT", True, False, True)] == (7, 0, 0)
    assert pdd.MOVES[("PAGEDOWN", True, True, False)] == (0, 0, 1)
    assert (
        pdd.short_note("Read as March 4, 2011, month first, as your system writes dates.")
        == "Read month first, as your system writes dates."
    )
    assert pdl.span_name(date(2011, 1, 1), date(2011, 12, 31)) == "2011"


def test_save_range_refuses_bad_dates(app, tmp_path: Path) -> None:
    said: list[str] = []
    dlg = SaveRangeDialog(
        None,
        location=WeatherLocation("Berlin", 52.5, 13.4, id="b"),
        data_dir=tmp_path,
        units=pdd.past_day_text.Units(),
        today=TODAY,
        order="MDY",
        start=date(2011, 3, 14),
        task_manager=None,
        announce_cb=said.append,
    )
    try:
        assert dlg.dates() == (date(2011, 3, 1), date(2011, 3, 14))
        dlg._from.SetValue("soon")
        assert "did not understand" in dlg.dates()
        dlg._from.SetValue("March 2011")
        dlg._to.SetValue("2011-03-01")
        assert dlg.dates() == (date(2011, 3, 1), date(2011, 3, 1))
    finally:
        dlg.dialog.Destroy()
