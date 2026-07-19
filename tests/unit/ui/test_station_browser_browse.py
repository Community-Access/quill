"""Browse-a-source-without-searching in the station browser (Kelly's request).

Drives the new category/genre logic against fakes (the dialog needs a live
wx.App to fully construct), verifying the routing and genre-picker population
headlessly. The source catalogs themselves (SomaFM, NFB, Community M3U) are
unit-tested in their own core modules.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.ui.radio.station_browser_dialog import (
    _CATEGORIES,
    _M3U_GENRES,
    _NFB_RADIO,
    _POPULAR,
    _SOMAFM,
    StationBrowserDialog,
)


class _FakeChoice:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.enabled = False
        self.selection = -1

    def Set(self, items: list[str]) -> None:  # noqa: N802 - wx shape
        self.items = list(items)

    def Enable(self, value: bool) -> None:  # noqa: N802
        self.enabled = value

    def GetSelection(self) -> int:  # noqa: N802
        return self.selection

    def GetCount(self) -> int:  # noqa: N802
        return len(self.items)


class _FakeStatus:
    def __init__(self) -> None:
        self.label = ""

    def SetLabel(self, text: str) -> None:  # noqa: N802
        self.label = text


def _dialog() -> Any:
    d = StationBrowserDialog.__new__(StationBrowserDialog)
    d._safe_mode = False
    d._genre_ctrl = _FakeChoice()
    d._genre_slugs = []
    d._status = _FakeStatus()
    d._announced: list[str] = []
    d._announce = d._announced.append
    d._filled: list[tuple[list, str]] = []
    d._fill_results = lambda stations, *, status: d._filled.append((stations, status))
    d._category_list = SimpleNamespace(
        GetSelection=lambda: _CATEGORIES.index(_M3U_GENRES),
        SetSelection=lambda i: None,
    )
    d._wx = SimpleNamespace(NOT_FOUND=-1)
    return d


def test_show_nfb_category_fills_the_bundled_station() -> None:
    d = _dialog()
    d._show_category(_NFB_RADIO)
    stations, status = d._filled[-1]
    assert len(stations) == 1
    assert "NFBRN" in stations[0].name
    assert "National Federation of the Blind" in status
    assert d._genre_ctrl.enabled is False  # genre picker only for Music Genres


def test_popular_and_somafm_categories_browse_async() -> None:
    # Both fetch off-thread via _browse_async (no query); stub it to capture.
    for category, needle in ((_POPULAR, "popular"), (_SOMAFM, "SomaFM")):
        d = _dialog()
        captured: dict = {}
        d._browse_async = lambda fetch, *, loading, done, error, _c=captured: _c.update(
            loading=loading, error=error
        )
        d._show_category(category)
        assert needle.lower() in (captured["loading"] + captured["error"]).lower(), category
        assert d._genre_ctrl.enabled is False  # genre picker only for Music Genres


def test_apply_genres_m3u_populates_and_credits_junguler() -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._apply_genres(["acid_jazz", "rock"])
    assert d._genre_slugs == ["acid_jazz", "rock"]
    assert d._genre_ctrl.items == ["Acid Jazz", "Rock"]  # humanized labels
    assert d._genre_ctrl.enabled is True
    assert "junguler" in d._status.label  # attribution to the catalog author


def test_apply_genres_xiph_credits_the_directory() -> None:
    from quill.core.radio import xiph

    d = _dialog()
    d._genre_source = xiph
    d._apply_genres(["Jazz"])
    assert d._genre_ctrl.items == ["Jazz"]
    assert "Xiph" in d._status.label or "Icecast" in d._status.label


def test_apply_genres_empty_reports_and_disables() -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._apply_genres([])
    assert d._genre_ctrl.enabled is False
    assert "Refresh" in d._status.label


def test_on_genre_selected_browses_that_genre(monkeypatch) -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._genre_slugs = ["jazz", "rock"]
    d._genre_ctrl.selection = 1  # "rock"
    captured: dict = {}
    d._browse_async = lambda fetch, *, loading, done, error: captured.update(
        loading=loading, done1=done(1), error=error
    )
    d._on_genre_selected(None)
    assert "Rock" in captured["loading"]
    assert "Rock station" in captured["done1"]
    assert "Rock" in captured["error"]


def test_on_genre_selected_ignores_no_selection() -> None:
    from quill.core.radio import m3u_catalog

    d = _dialog()
    d._genre_source = m3u_catalog
    d._genre_slugs = ["jazz"]
    d._genre_ctrl.selection = -1
    d._browse_async = lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not browse"))
    d._on_genre_selected(None)  # no-op, no exception


def _tunein_row(kind: str, guide_id: str = "c9"):
    from quill.core.radio import tunein
    from quill.core.radio.tunein import TuneInResult

    if kind == "up":
        return tunein.nav_up_row()
    return tunein.browse_row_to_station(
        TuneInResult(guide_id=guide_id, title="Music", is_station=(kind == "station"))
    )


def _play_dialog(selected):
    calls: list[str] = []
    d = StationBrowserDialog.__new__(StationBrowserDialog)
    d._tunein_stack = ["c1"]
    d._selected_station = lambda: selected
    d._tunein_browse = lambda gid: calls.append(f"browse:{gid!r}")
    d._play_tunein_station = lambda station, gid: calls.append(f"resolve:{gid}")
    d._controller = SimpleNamespace(
        play_station=lambda s: calls.append(f"play:{s.name}"), stop=lambda: None
    )
    d._is_station_playing = lambda s: False
    d._announce = lambda m: None
    d._refresh_play_button = lambda: None
    return d, calls


def test_tunein_category_row_drills_in() -> None:
    d, calls = _play_dialog(_tunein_row("category", "c42"))
    d._on_play(None)
    assert calls == ["browse:'c42'"]
    assert d._tunein_stack == ["c1", "c42"]  # pushed


def test_tunein_up_row_pops_and_rebrowses() -> None:
    d, calls = _play_dialog(_tunein_row("up"))
    d._on_play(None)
    assert d._tunein_stack == []  # popped the only entry
    assert calls == ["browse:''"]  # back to top level


def test_tunein_station_row_resolves_then_plays() -> None:
    d, calls = _play_dialog(_tunein_row("station", "s500"))
    d._on_play(None)
    assert calls == ["resolve:s500"]


def test_normal_station_still_plays_directly() -> None:
    from quill.core.radio.models import RadioStation

    d, calls = _play_dialog(RadioStation(name="WXYZ", stream_url="https://x/s", station_uuid="u1"))
    d._on_play(None)
    assert calls == ["play:WXYZ"]  # untouched by the TuneIn nav handling


def test_tunein_browse_done_builds_up_and_rows() -> None:
    from quill.core.radio.tunein import TuneInResult

    d = StationBrowserDialog.__new__(StationBrowserDialog)
    d._tunein_stack = ["c1"]  # drilled in -> an Up row is prepended
    d._filled: list = []
    d._fill_results = lambda rows, *, status: d._filled.append((rows, status))
    d._announce = lambda m: None
    results = [
        TuneInResult(guide_id="c2", title="Jazz", is_station=False),
        TuneInResult(guide_id="s9", title="Jazz FM", is_station=True),
    ]
    d._tunein_browse_done(results)
    rows, status = d._filled[-1]
    assert rows[0].name == "[Up one level]"
    assert len(rows) == 3  # up + category + station
    assert "1 categor" in status and "1 station" in status


def test_on_refresh_routes_to_genres_when_music_genres_active() -> None:
    d = _dialog()  # category_list reports Music Genres
    calls: list[str] = []
    d._load_genres = lambda: calls.append("genres")
    d._on_refresh_directory = lambda _e: calls.append("iheart")
    d._on_refresh(None)
    assert calls == ["genres"]
    assert d._genre_source.CATEGORY_LABEL == "Community M3U"  # source set for the refresh


def test_on_refresh_routes_to_iheart_for_other_categories() -> None:
    d = _dialog()
    d._category_list = SimpleNamespace(GetSelection=lambda: _CATEGORIES.index("Search Results"))
    calls: list[str] = []
    d._load_genres = lambda: calls.append("genres")
    d._on_refresh_directory = lambda _e: calls.append("iheart")
    d._on_refresh(None)
    assert calls == ["iheart"]
