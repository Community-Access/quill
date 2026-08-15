"""Searching every library at once -- and admitting which ones cannot be asked.

Quill Radio 3.0 grew fifteen browse branches while Find Stations kept searching
the same eight radio directories. These pin the half that closes it, and in
particular the honesty requirements: a source that *cannot* be searched is a
different fact from one that found nothing, and one source failing must never
sink the search.
"""

from __future__ import annotations

import pytest

from quill.core.radio import federated_search as fs
from quill.core.radio.models import RadioStation


def _station(name: str, url: str = "", source: str = "LibriVox") -> RadioStation:
    return RadioStation(name=name, stream_url=url, source=source)


def test_every_source_that_publishes_a_search_is_searched() -> None:
    # Audius, Mixcloud and ccMixter were listed here as unsearchable -- trending,
    # categories and tags respectively -- until somebody checked the services
    # and found all three publish a keyword search (2026-08-14). The browse tree
    # offered shelves because shelves are good, not because the services could
    # not be asked a question, and "this cannot be searched" was a claim about
    # somebody else's product that was not true.
    assert set(fs.searchable_ids()) == {
        "librivox",
        "gutenberg",
        "archive",
        "apple_podcasts",
        "audius",
        "mixcloud",
        "ccmixter",
    }


def test_a_source_that_cannot_search_still_has_somewhere_honest_to_say_so() -> None:
    # Nothing is unsearchable today. The machinery stays because the next source
    # added may genuinely lack a search, and having nowhere to record that is
    # what let three wrong claims sit unchallenged for a release.
    for source in fs.LIBRARY_SOURCES:
        assert source.search is not None or source.unsearchable_because, source.id


def test_every_source_declares_a_group_the_list_can_show() -> None:
    for source in fs.LIBRARY_SOURCES:
        assert source.group in fs.GROUP_ORDER, source.id


def test_results_are_grouped_and_ordered_for_reading() -> None:
    results = fs.FederatedResults()
    results.add(fs.GROUP_PODCASTS, [_station("A Show", "u1", "Podcasts (Apple)")])
    results.add(fs.GROUP_AUDIOBOOKS, [_station("A Book", "u2")])
    # Declaration order must not decide reading order.
    assert [name for name, _rows in results.ordered()] == [
        fs.GROUP_AUDIOBOOKS,
        fs.GROUP_PODCASTS,
    ]
    assert results.total == 2


def test_an_empty_group_is_not_shown() -> None:
    results = fs.FederatedResults()
    results.add(fs.GROUP_STATIONS, [])
    assert results.ordered() == []


def test_the_same_thing_twice_is_listed_once() -> None:
    rows = [_station("A", "https://x/1"), _station("A again", "https://x/1")]
    assert len(fs.dedupe(rows)) == 1
    # First answer wins: a source's own order is the only ranking trusted here.
    assert fs.dedupe(rows)[0].name == "A"


def test_rows_with_no_stream_fall_back_to_a_stable_identity() -> None:
    # A LibriVox book and an Archive item have no stream on the row -- the tree
    # resolves them -- so dedupe must not collapse them all onto "".
    rows = [_station("Book One"), _station("Book Two"), _station("Book One")]
    assert [r.name for r in fs.dedupe(rows)] == ["Book One", "Book Two"]


def test_one_failing_source_never_sinks_the_search(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_query: str, _safe: bool) -> list:
        raise OSError("the library is down")

    def _ok(_query: str, _safe: bool) -> list:
        return [_station("A Book", "u1")]

    monkeypatch.setattr(
        fs,
        "LIBRARY_SOURCES",
        (
            fs.LibrarySource("a", "Alpha", fs.GROUP_AUDIOBOOKS, _boom),
            fs.LibrarySource("b", "Beta", fs.GROUP_AUDIOBOOKS, _ok),
        ),
    )
    results = fs.search_all("anything")
    assert results.total == 1
    assert results.failed == [("Alpha", "the library is down")]


def test_an_empty_query_asks_nobody(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def _record(query: str, _safe: bool) -> list:
        called.append(query)
        return []

    monkeypatch.setattr(
        fs, "LIBRARY_SOURCES", (fs.LibrarySource("a", "Alpha", fs.GROUP_AUDIOBOOKS, _record),)
    )
    assert fs.search_all("   ").total == 0
    assert called == []
    assert fs.search_source("a", "  ") == []


def test_the_summary_counts_then_caveats() -> None:
    results = fs.FederatedResults()
    results.add(fs.GROUP_AUDIOBOOKS, [_station("A", "u1"), _station("B", "u2")])
    results.add(fs.GROUP_PODCASTS, [_station("C", "u3", "Podcasts (Apple)")])
    results.failed = [("Internet Archive", "timed out")]
    results.unsearchable = [("Mixcloud", "browsed by category")]

    said = fs.describe(results)
    assert said.startswith("3 found: 2 in Audiobooks, 1 in Podcasts.")
    assert "Internet Archive could not be reached" in said
    # The caveat comes last, because it is not a result.
    assert said.index("could not be reached") < said.index("browsed but not searched")


def test_nothing_found_still_says_what_could_not_be_asked() -> None:
    results = fs.FederatedResults()
    results.unsearchable = [("Audius", "trending only")]
    said = fs.describe(results)
    assert said.startswith("Nothing found in the libraries.")
    assert "Audius can be browsed but not searched" in said


def test_an_unknown_source_id_is_not_an_error() -> None:
    assert fs.source("nope") is None
    assert fs.search_source("nope", "jazz") == []
