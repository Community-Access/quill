"""Search pagination in the station browser (issue #1064).

Raising the per-request limit to 200 and adding a More Stations button that
pages the RadioBrowser search. Drives the done-handlers against fakes (the
dialog needs a live wx.App to construct) so the paging bookkeeping is verified
headlessly. The pure summary helper is covered directly.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.models import RadioStation
from quill.ui.radio.station_browser_dialog import (
    _SEARCH_LIMIT,
    StationBrowserDialog,
    _search_result_summary,
)


def _station(name: str) -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://example.com/{name}", station_uuid=name)


class _FakeButton:
    def __init__(self) -> None:
        self.enabled = False

    def Enable(self, value: bool) -> None:  # noqa: N802 - wx shape
        self.enabled = value


class _FakeList:
    def __init__(self) -> None:
        self.selected: int | None = None

    def Select(self, index: int) -> None:  # noqa: N802
        self.selected = index

    def Focus(self, index: int) -> None:  # noqa: N802
        self.selected = index

    def EnsureVisible(self, index: int) -> None:  # noqa: N802
        pass


class _FakeStatus:
    def __init__(self) -> None:
        self.label = ""

    def SetLabel(self, text: str) -> None:  # noqa: N802
        self.label = text


def _dialog() -> Any:
    d = StationBrowserDialog.__new__(StationBrowserDialog)
    d._search_btn = _FakeButton()
    d._more_btn = _FakeButton()
    d._status = _FakeStatus()
    d._results = _FakeList()
    d._current_results = []
    d._search_results = []
    d._search_rb = []
    d._search_soma = []
    d._search_offset = 0
    d._search_more_available = False
    d._announced: list[str] = []
    d._announce = d._announced.append
    # _show_category re-fills the visible list; stub it to mirror the search
    # results into _current_results without touching wx.
    d._show_category = lambda _cat: setattr(d, "_current_results", list(d._search_results))
    return d


def test_full_first_page_enables_more_and_flags_available() -> None:
    dialog = _dialog()
    radio = [_station(f"r{i}") for i in range(_SEARCH_LIMIT)]
    soma = [_station("SomaFM Groove")]
    dialog._on_search_done((radio, soma), None)
    assert dialog._search_more_available is True
    assert dialog._more_btn.enabled is True
    assert len(dialog._search_results) == _SEARCH_LIMIT + 1
    assert dialog._search_offset == _SEARCH_LIMIT
    assert "More Stations" in dialog._announced[0]


def test_short_first_page_disables_more() -> None:
    dialog = _dialog()
    dialog._on_search_done(([_station("only")], []), None)
    assert dialog._search_more_available is False
    assert dialog._more_btn.enabled is False
    assert dialog._announced[0] == "1 station found."


def test_more_appends_next_page_after_radiobrowser_before_soma() -> None:
    dialog = _dialog()
    radio = [_station(f"r{i}") for i in range(_SEARCH_LIMIT)]
    soma = [_station("SomaFM Groove")]
    dialog._on_search_done((radio, soma), None)
    first_new = len(dialog._search_results)

    page2 = [_station(f"r{i}") for i in range(_SEARCH_LIMIT, _SEARCH_LIMIT + 40)]
    dialog._on_more_done(page2, None)

    # New RadioBrowser rows join the RadioBrowser half; SomaFM stays at the end.
    assert dialog._search_results[-1].name == "SomaFM Groove"
    assert dialog._search_rb[-1].name == f"r{_SEARCH_LIMIT + 39}"
    assert len(dialog._search_results) == _SEARCH_LIMIT + 40 + 1
    # A 40-row page is short of the cap, so there is no further page.
    assert dialog._search_more_available is False
    assert dialog._more_btn.enabled is False
    # Focus lands on the first newly added station.
    assert dialog._results.selected == first_new
    assert "Added 40 more" in dialog._announced[-1]


def test_more_error_keeps_button_enabled_for_retry() -> None:
    dialog = _dialog()
    dialog._search_more_available = True
    dialog._on_more_done([], RuntimeError("network hiccup"))
    assert dialog._more_btn.enabled is True
    assert "Could not load more" in dialog._status.label


def test_search_error_reports_and_does_not_crash() -> None:
    dialog = _dialog()
    dialog._on_search_done(([], []), RuntimeError("boom"))
    assert "Search failed" in dialog._status.label


def test_summary_wording() -> None:
    assert _search_result_summary(0) == "No stations found. Try a different name, tag, or country."
    assert _search_result_summary(1) == "1 station found."
    assert _search_result_summary(12) == "12 stations found."
    assert "More Stations" in _search_result_summary(200, more=True)
