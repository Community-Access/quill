"""What the Find Streams list shows and says (quill.core.radio.find_streams_view)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.radio import find_streams_view as view
from quill.core.radio.find_streams_view import ViewState
from quill.core.radio.page_links import PageStreamCandidate


def _c(url: str, check: str = "live", **fields: Any) -> PageStreamCandidate:
    candidate = PageStreamCandidate(url=url, reason="audio tag", check=check)
    for name, value in fields.items():
        setattr(candidate, name, value)
    return candidate


def _list() -> list[PageStreamCandidate]:
    return [
        _c("https://a.example/zulu", stream_name="Zulu FM", codec="MP3", bitrate_kbps=64),
        _c("https://a.example/alpha", stream_name="Alpha FM", codec="AAC", bitrate_kbps=128),
        _c("https://a.example/echo", stream_name="Echo FM", codec="Ogg Opus"),
        _c("https://a.example/slow", "not checked", check_note="it took too long to answer"),
        _c("https://a.example/ep.mp3", "file", stream_name="Bravo episode", codec="MP3"),
    ]


def test_scan_order_is_the_order_the_scan_gave() -> None:
    assert view.visible(_list(), ViewState()) == [0, 1, 2, 3, 4]


def test_name_order_keeps_the_groups() -> None:
    # Live rows A to Z, then not checked, then files: "Live:" stays first.
    assert view.visible(_list(), ViewState(order=view.NAME)) == [1, 2, 0, 3, 4]


def test_bitrate_highest_first_and_unknowns_last() -> None:
    assert view.visible(_list(), ViewState(order=view.BITRATE)) == [1, 0, 2, 3, 4]


def test_listeners_only_with_counts() -> None:
    rows = _list()
    assert not view.has_listeners(rows)
    assert view.visible(rows, ViewState(order=view.LISTENERS)) == [0, 1, 2, 3, 4]
    rows[2].listeners = 40
    rows[0].listeners = 3
    assert view.visible(rows, ViewState(order=view.LISTENERS)) == [2, 0, 1, 3, 4]


def test_formats_and_the_filter() -> None:
    rows = _list()
    assert [view.format_of(c) for c in rows] == ["MP3", "AAC", "Opus", "", "MP3"]
    assert view.formats_present(rows) == ["MP3", "AAC", "Opus"]
    assert view.visible(rows, ViewState(format="MP3")) == [0, 4]
    assert view.visible(rows, ViewState(live_only=True)) == [0, 1, 2]
    assert view.visible(rows, ViewState(format="MP3", live_only=True)) == [0]
    assert view.visible(rows, ViewState(format="HLS")) == []


@pytest.mark.parametrize(
    ("order", "sentence"),
    [
        (view.SCAN, "Back in scan order."),
        (view.NAME, "Sorted by name, A to Z."),
        (view.BITRATE, "Sorted by bitrate, highest first."),
        (view.LISTENERS, "Sorted by listeners, most first."),
    ],
)
def test_order_sentences(order: str, sentence: str) -> None:
    assert view.order_sentence(order) == sentence


def test_shown_and_empty_sentences() -> None:
    assert view.shown_sentence(4, 31, ViewState(format="MP3")) == "Showing 4 of 31 links: MP3 only."
    assert (
        view.shown_sentence(12, 31, ViewState(live_only=True))
        == "Showing 12 of 31 links: live streams only."
    )
    assert (
        view.shown_sentence(3, 31, ViewState(format="MP3", live_only=True))
        == "Showing 3 of 31 links: live MP3 streams only."
    )
    assert view.shown_sentence(31, 31, ViewState()) == "Showing all 31 links."
    assert (
        view.empty_filter_sentence(ViewState(format="AAC", live_only=True))
        == "No links are live AAC streams, so the list is unchanged."
    )


def test_rows_that_would_read_the_same_are_told_apart() -> None:
    rows = [
        _c("https://ice1.example.org/live", stream_name="WXYZ"),
        _c("https://ice2.example.org/live", stream_name="WXYZ"),
        _c("https://ice2.example.org/live/", stream_name="WXYZ"),
        _c("https://other.example/x", stream_name="Other"),
    ]
    assert view.distinct_rows(rows) == [
        "Live: WXYZ (ice1.example.org/live)",
        "Live: WXYZ (ice2.example.org/live)",
        "Live: WXYZ (ice2.example.org/live) (link 2)",
        "Live: Other",
    ]


def _find(rows: list[PageStreamCandidate], term: str, start: int, **kw: Any) -> Any:
    shown = kw.pop("shown", list(range(len(rows))))
    return view.find(rows, view.distinct_rows(rows), shown, term, start, **kw)


def test_find_wraps_and_ignores_case_and_accents() -> None:
    rows = _list()
    rows[1].stream_name = "Écho Alpha"
    assert _find(rows, "echo", 0).position == 1
    assert _find(rows, "ECHO", 1).position == 2
    assert _find(rows, "echo", 2).position == 1  # wrapped, silently
    assert _find(rows, "echo", 2).sentence == ""
    assert _find(rows, "echo", 2, backwards=True).position == 1


def test_find_reads_the_link_and_how_it_was_found() -> None:
    rows = _list()
    rows[3].reason = "Listen link (found via player page)"
    assert _find(rows, "player page", 0).position == 3
    assert _find(rows, "ep.mp3", 0).position == 4
    assert _find(rows, "128 kbps", 0).position == 1


def test_find_says_what_it_could_not_do() -> None:
    rows = _list()
    assert _find(rows, "lush", 0).sentence == "Nothing in the list matches 'lush'."
    hidden = _find(rows, "bravo", 0, shown=[0, 1, 2])
    assert hidden.position is None
    assert (
        hidden.sentence
        == "Nothing shown matches 'bravo'; 1 link that does is hidden by the filter."
    )
    only = _find(rows, "zulu", 0)
    assert (only.position, only.sentence) == (0, "That is the only match.")


def test_select_all_sentences() -> None:
    assert view.select_all_sentence(False, 31, 31) == "Selected all 31 links."
    assert view.select_all_sentence(False, 4, 31) == "Selected all 4 links shown."
    assert view.select_all_sentence(True, 31, 31) == "All 31 links are already selected."


def test_action_sentences_always_carry_the_count() -> None:
    assert view.added_sentence(["WXYZ FM"], 1, 0) == "Added WXYZ FM to Favorites."
    assert (
        view.added_sentence(["a", "b", "c"], 3, 0, "WXYZ")
        == "Added 3 streams to Favorites, in the folder WXYZ."
    )
    assert (
        view.added_sentence(["a", "b", "c"], 2, 1)
        == "Added 2 streams to Favorites; 1 was already there."
    )
    assert view.added_sentence(["a", "b"], 0, 2) == "All 2 streams were already in your Favorites."
    assert view.added_sentence(["WXYZ FM"], 0, 1) == "WXYZ FM is already in your Favorites."
    assert view.saved_sentence(3, "WXYZ.m3u") == "Saved 3 streams to WXYZ.m3u."
    assert view.copied_sentence(3) == "Copied 3 stream links."
    assert view.copied_sentence(1) == "Copied the stream link."


@pytest.mark.parametrize(
    ("url", "reason", "expected"),
    [
        ("http://radio.example.net:8000/live", "audio tag", "http://radio.example.net:8000/"),
        ("https://www.station.example/stream", "audio tag", ""),  # the page's own host
        ("http://192.168.1.9:8000/live", "audio tag", ""),  # your own network
        ("https://18373.live.streamtheworld.com/KKSEFM", "audio tag", ""),  # a resolver
        ("https://cdn.example.akamaized.net/a.aac", "audio tag", ""),  # a CDN
        ("https://radio.example.net/hls/live.m3u8", "audio tag", ""),  # HLS
        ("http://radio.example.net:8000/jazz", "stream listed by the SHOUTcast server", ""),
    ],
)
def test_scan_this_streams_server_only_when_it_would_list_something(
    url: str, reason: str, expected: str
) -> None:
    candidate = _c(url, reason=reason)
    assert view.server_to_scan(candidate, "https://station.example/") == expected
