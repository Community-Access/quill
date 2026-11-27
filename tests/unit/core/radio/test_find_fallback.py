"""Find Streams' other ways: what counts as a name, the order tried, the sentences."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.radio import find_fallback as fb
from quill.core.radio import find_fallback_io as io
from quill.core.radio import link_finder, radio_browser
from quill.core.radio.link_finder import PageScanResult
from quill.core.radio.models import RadioStation
from quill.core.radio.page_links import PageStreamCandidate


@pytest.mark.parametrize(
    ("typed", "kind"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("kexp", "name"),
        ("bbcradio4", "name"),
        ("BBC Radio 4", "name"),
        ("kexp.mp3", "name"),
        ("kexp.PLS", "name"),
        ("kexp.org", "address"),
        ("www.kexp.org/listen", "address"),
        ("https://kexp.org", "address"),
        ("http://x.example/stream.mp3", "address"),
        ("x.example/stream.mp3", "address"),
        ("radio.example.mp3", "address"),
    ],
)
def test_typed_kind(typed: str, kind: str) -> None:
    assert fb.typed_kind(typed) == kind


def test_name_query_drops_the_ending_and_punctuation() -> None:
    assert fb.name_query("kexp.mp3") == "kexp"
    assert fb.name_query("  my_radio-one.m3u ") == "my radio one"
    assert fb.compact("BBC Radio 4") == fb.compact("bbcradio4") == "bbcradio4"


@pytest.mark.parametrize(
    ("address", "name"),
    [
        ("https://www.kexp.org/listen", "kexp"),
        ("http://stream.example.co.uk/a", "example"),
        ("kexp.org", "kexp"),
        ("localhost", "localhost"),
    ],
)
def test_site_name(address: str, name: str) -> None:
    assert fb.site_name(address) == name


def test_a_typed_name_matches_a_recent_site_only_by_its_whole_name() -> None:
    recent = ["https://www.kexp.org/listen", "https://wfmu.org/"]
    assert fb.matching_recent_site("kexp", recent) == recent[0]
    assert fb.matching_recent_site("KEXP.mp3", recent) == recent[0]
    assert fb.matching_recent_site("kex", recent) == ""
    assert fb.matching_recent_site("wf", recent) == ""  # too short to guess from
    assert fb.matching_recent_site("nts", recent) == ""


def _station(name: str, url: str, source: str = "") -> RadioStation:
    return RadioStation(name=name, stream_url=url, source=source)


def test_directory_rows_match_ignoring_spaces_exact_first_and_once() -> None:
    stations = [
        _station("BBC Radio 4 Extra", "http://a/extra"),
        _station("BBC Radio 4", "http://a/four"),
        _station("BBC Radio 4", "http://a/four"),  # the same stream twice
        _station("Radio 40", "http://a/forty"),
        _station("Jazz FM", "http://a/jazz"),
        _station("", ""),
    ]
    rows = fb.directory_candidates(stations, "bbcradio4")
    assert [r.url for r in rows] == ["http://a/four", "http://a/extra"]
    assert rows[0].label_is_name and rows[0].reason == "found in the Radio Browser directory"
    assert fb.directory_candidates(stations, "") == []


def _rows(n: int) -> list[PageStreamCandidate]:
    return [PageStreamCandidate(url=f"http://s/{i}", reason="x") for i in range(n)]


def test_an_address_that_works_never_touches_the_directories() -> None:
    calls: list[str] = []

    def directories(query: str) -> list[PageStreamCandidate]:
        calls.append(query)
        return []

    outcome, _ = fb.run(
        "address",
        scan_website=lambda: (_rows(2), "scan"),
        search_directories=directories,
        query="kexp",
        fallback=True,
    )
    assert outcome.method == fb.METHOD_WEBSITE and calls == []
    assert fb.found_by_sentence(outcome) == ""


def test_an_address_with_no_stream_stays_put_when_the_setting_is_off() -> None:
    calls: list[str] = []

    def directories(query: str) -> list[PageStreamCandidate]:
        calls.append(query)
        return _rows(1)

    outcome, _ = fb.run(
        "address",
        scan_website=lambda: ([], "scan"),
        search_directories=directories,
        query="kexp",
        fallback=False,
    )
    assert outcome.candidates == [] and calls == [] and outcome.method == ""


def test_the_directories_follow_the_website_when_the_setting_is_on() -> None:
    outcome, scan = fb.run(
        "address",
        scan_website=lambda: ([], "scan"),
        search_directories=lambda q: _rows(3) if q == "kexp" else [],
        query="kexp",
        fallback=True,
    )
    assert scan == "scan" and outcome.method == fb.METHOD_DIRECTORY
    assert [a.method for a in outcome.attempts] == [fb.METHOD_WEBSITE, fb.METHOD_DIRECTORY]
    assert fb.found_by_sentence(outcome) == (
        "The website had none, so these were found by the public directories "
        "(Radio Browser and IPRD)."
    )


def test_a_name_goes_straight_to_the_directories_whatever_the_setting() -> None:
    called: list[str] = []

    def website() -> tuple[list[PageStreamCandidate], object]:
        called.append("site")
        return [], None

    outcome, _ = fb.run(
        "name",
        scan_website=website,
        search_directories=lambda q: _rows(1),
        query="kexp",
        fallback=False,
    )
    assert called == [] and outcome.method == fb.METHOD_DIRECTORY
    assert fb.found_by_sentence(outcome) == (
        "Found by the public directories (Radio Browser and IPRD)."
    )


def test_describe_attempts() -> None:
    attempts = [fb.Attempt(fb.METHOD_WEBSITE, 0), fb.Attempt(fb.METHOD_DIRECTORY, 0)]
    assert fb.describe_attempts(attempts) == (
        "Tried the website and the public directories (Radio Browser and IPRD)."
    )
    assert fb.describe_attempts([]) == ""


# -- the real wiring, with fake scanners -------------------------------------------


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"scans": [], "scan": PageScanResult("T", "", [], checked=True)}

    def scan(url: str, **_k: Any) -> PageScanResult:
        state["scans"].append(url)
        if isinstance(state["scan"], BaseException):
            raise state["scan"]
        return state["scan"]

    def browse(query: str, **_k: Any) -> list[RadioStation]:
        return [_station("KEXP 90.3", "http://rb/kexp")] if "kexp" in query else []

    monkeypatch.setattr(link_finder, "scan_page_for_streams", scan)
    monkeypatch.setattr(radio_browser, "search_stations", browse)
    monkeypatch.setattr(io.iprd, "search_stations", lambda q, **_k: [])
    monkeypatch.setattr(io.iprd, "catalog", lambda **_k: [])
    monkeypatch.setattr(
        link_finder, "_apply_live_check", lambda rows, *_a, **_k: (list(rows), 0, 0)
    )
    return state


def test_find_a_name_without_spaces_and_with_an_ending(fakes: dict[str, Any]) -> None:
    for typed in ("kexp", "kexp.mp3"):
        found = io.find(typed, safe_mode=False, fallback=False)
        assert [c.url for c in found.scan.candidates] == ["http://rb/kexp"]
        assert found.how == "Found by the public directories (Radio Browser and IPRD)."
    assert fakes["scans"] == []  # a name is never sent to the website scanner


def test_fallback_on_finds_by_site_name_and_says_so(fakes: dict[str, Any]) -> None:
    found = io.find("https://www.kexp.org/", safe_mode=False, fallback=True)
    assert fakes["scans"] == ["https://www.kexp.org/"]
    assert found.how.startswith("The website had none")
    assert found.scan.candidates[0].url == "http://rb/kexp"


def test_fallback_off_keeps_the_empty_website_result(fakes: dict[str, Any]) -> None:
    found = io.find("https://www.kexp.org/", safe_mode=False, fallback=False)
    assert found.scan.candidates == [] and found.how == ""


def test_an_unreadable_page_raises_unless_another_way_finds_something(
    fakes: dict[str, Any],
) -> None:
    fakes["scan"] = link_finder.LinkFinderError("down")
    with pytest.raises(link_finder.LinkFinderError):
        io.find("https://nothing.example/", safe_mode=False, fallback=True)
    found = io.find("https://www.kexp.org/", safe_mode=False, fallback=True)
    assert found.scan.candidates  # the directories rescued it


def test_safe_mode_contacts_no_directory(fakes: dict[str, Any]) -> None:
    assert io.search_directories("kexp", safe_mode=True) == []
