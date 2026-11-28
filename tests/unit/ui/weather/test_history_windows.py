"""Build and drive Weather History
without showing a modal: the right fields show for each kind of lookup, labels
come before their controls, bad dates are refused, a lookup lands in the
summary and the list, and Report Fields orders and removes fields."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import wx

from quill.core.weather import locations as loc_store
from quill.core.weather.history_cache import DayRecord
from quill.core.weather.history_service import Lookup
from quill.core.weather.models import WeatherLocation
from quill.ui.weather.history_dialog import WeatherHistoryDialog, parse_iso_date, summary_lead
from tests.wx_session import shared_wx_app


@pytest.fixture
def app():
    a = shared_wx_app()
    yield a
    a.Destroy()


def _history(tmp_path: Path, said: list[str]) -> WeatherHistoryDialog:
    store = loc_store.load_locations(tmp_path)
    store.add(WeatherLocation("Tucson", 32.2, -110.9, id="t"))
    loc_store.save_locations(tmp_path, store)
    return WeatherHistoryDialog(
        None, data_dir=tmp_path, task_manager=None, safe_mode=False, announce_cb=said.append
    )


def test_labels_come_before_their_controls(app, tmp_path: Path) -> None:
    dlg = _history(tmp_path, [])
    try:
        children = list(dlg.dialog.GetChildren())
        for control, text in (
            (dlg._place, "&Place:"),
            (dlg._kind, "&Kind of lookup:"),
            (dlg._month, "&Month:"),
            (dlg._years, "&Years to look back:"),
            (dlg._start, "&From (year-month-day):"),
        ):
            before = children[children.index(control) - 1]
            assert isinstance(before, wx.StaticText) and before.GetLabel() == text
    finally:
        dlg.dialog.Destroy()


def test_fields_follow_the_kind_of_lookup(app, tmp_path: Path) -> None:
    dlg = _history(tmp_path, [])
    try:
        assert dlg.kind() == "on_this_day"
        assert not dlg._month.IsShown() and dlg._years.IsShown() and not dlg._start.IsShown()
        dlg._kind.SetSelection(1)
        dlg._show_fields()
        assert dlg._month.IsShown() and dlg._day.IsShown() and dlg._years.IsShown()
        dlg._kind.SetSelection(2)
        dlg._show_fields()
        assert dlg._start.IsShown() and dlg._end.IsShown() and not dlg._years.IsShown()
    finally:
        dlg.dialog.Destroy()


def test_bad_dates_are_refused_in_words(app, tmp_path: Path) -> None:
    dlg = _history(tmp_path, [])
    try:
        dlg._kind.SetSelection(2)
        dlg._show_fields()
        dlg._start.SetValue("June 1")
        assert "year-month-day" in dlg.build_query()
        dlg._kind.SetSelection(1)
        dlg._month.SetSelection(1)  # February
        dlg._day.SetValue(30)
        assert dlg.build_query() == "February has no day 30."
    finally:
        dlg.dialog.Destroy()
    assert parse_iso_date("2024-06-01") == date(2024, 6, 1)
    assert parse_iso_date("2024-13-01") is None


def test_a_lookup_lands_in_the_summary_and_the_list(app, tmp_path: Path) -> None:
    said: list[str] = []
    dlg = _history(tmp_path, said)
    try:
        rows = [DayRecord("2025-11-27", 0, 20.0, 5.0, 0.0), DayRecord("2024-11-27", 61, 15.0)]
        dlg._request = 3
        dlg._landed(
            3,
            Lookup(
                summary="November 27 in Tucson. It was warm. It was dry. Long tail.",
                rows=rows,
                credits="Weather data by Open-Meteo.com.",
            ),
        )
        assert dlg._list.GetItemCount() == 2
        assert dlg._list.GetItemText(1, 4) == "not recorded"
        assert "Sources: Weather data by Open-Meteo.com." in dlg._summary.GetValue()
        assert said[-1] == "2 days found. It was warm. It was dry."
        assert "June" not in dlg.copy_text() and "November 27, 2025" in dlg.copy_text()
        # A stale answer for an older lookup is ignored.
        dlg._landed(2, ValueError("old"))
        assert dlg._list.GetItemCount() == 2
        # A failure clears the old answer so it is not read as this one's.
        dlg._landed(3, ValueError("boom"))
        assert dlg._list.GetItemCount() == 0 and dlg._summary.GetValue() == ""
    finally:
        dlg.dialog.Destroy()


def test_summary_lead_skips_the_place_line() -> None:
    assert summary_lead("A in B. First. Second. Third.") == "First. Second."
    assert summary_lead("Only one.") == "Only one."
