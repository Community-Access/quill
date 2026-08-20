"""Searching every source at once, answered in browse rows.

The behaviour these pin is the difference between the old Search All Sources
and the new one: the answer is a list of *browse* rows carrying their sources'
own node ids, so a found podcast show is the same object a browsed one is --
expandable, subscribable, and saying what it is.
"""

from __future__ import annotations

import pytest

from quill.core.radio import branch_find, federated_browse
from quill.core.radio.browse_nodes import folder, leaf
from quill.core.radio.models import RadioStation


def _station(name: str, url: str) -> RadioStation:
    return RadioStation(name=name, stream_url=url)


@pytest.fixture
def _routes(monkeypatch: pytest.MonkeyPatch) -> dict[str, tuple]:
    """Stand in for every network route, keyed by the seed id asked for."""
    answers: dict[str, tuple] = {}

    def fake_fast_find(node_id, query, *, safe_mode=False, catalog=None):
        return answers.get(node_id)

    monkeypatch.setattr(branch_find, "fast_find", fake_fast_find)
    return answers


def test_rows_say_what_they_are_and_who_answered(_routes: dict) -> None:
    _routes["apple"] = ([folder("appleshow:1", "Double Tap")], "searched the podcast directory")
    _routes["tunein"] = ([leaf(_station("Jazz FM", "http://a"))], "searched TuneIn")

    found = federated_browse.search_everything("tap", targets=federated_browse.TARGETS)

    notes = {row.label: row.note for row in found.rows}
    assert notes["Double Tap"] == "Podcast, Apple Podcasts"
    assert notes["Jazz FM"] == "Station, TuneIn"


def test_a_source_note_survives_the_annotation(_routes: dict) -> None:
    # A ccMixter licence, a "resolves when you play it" -- the source's own
    # word about the row is kept, after the type rather than instead of it.
    _routes["ccmixter"] = ([leaf(_station("A Track", "http://t"), note="CC BY 3.0")], "ok")

    found = federated_browse.search_everything("a", targets=federated_browse.TARGETS)

    assert found.rows[0].note == "Track, ccMixter, CC BY 3.0"


def test_folders_stay_folders_so_they_can_be_opened(_routes: dict) -> None:
    _routes["librivox"] = ([folder("librivoxbook:42", "Middlemarch")], "searched LibriVox")

    found = federated_browse.search_everything("middle", targets=federated_browse.TARGETS)

    assert found.rows[0].is_folder
    # The id is the one browsing would have produced: the menu and the expand
    # handler both dispatch on it, which is the whole point of this shape.
    assert found.rows[0].node_id == "librivoxbook:42"


def test_results_are_grouped_by_type_not_by_arrival(_routes: dict) -> None:
    _routes["librivox"] = ([folder("librivoxbook:1", "A Book")], "")
    _routes["apple"] = ([folder("appleshow:1", "A Show")], "")
    _routes["tunein"] = ([leaf(_station("A Station", "http://s"))], "")

    found = federated_browse.search_everything("a", targets=federated_browse.TARGETS)

    assert [row.label for row in found.rows] == ["A Station", "A Show", "A Book"]
    assert found.counts == {"Station": 1, "Podcast": 1, "Audiobook": 1}


def test_the_same_thing_from_two_directories_is_listed_once(_routes: dict) -> None:
    same = _station("Jazz FM", "http://same")
    _routes["tunein"] = ([leaf(same)], "")
    _routes["iheart"] = ([leaf(same)], "")

    found = federated_browse.search_everything("jazz", targets=federated_browse.TARGETS)

    assert [row.label for row in found.rows] == ["Jazz FM"]


def test_a_source_that_could_not_be_reached_is_named(_routes: dict) -> None:
    _routes["tunein"] = ([], f"tunein {branch_find.UNREACHABLE}")
    _routes["apple"] = ([folder("appleshow:1", "A Show")], "ok")

    found = federated_browse.search_everything("x", targets=federated_browse.TARGETS)

    assert [label for label, _why in found.failed] == ["TuneIn"]
    assert "TuneIn could not be reached" in federated_browse.describe("x", found)


def test_an_empty_answer_is_not_a_failure(_routes: dict) -> None:
    # Nothing matched and nobody was unreachable: saying a source failed here
    # would send somebody hunting a network problem that is not there.
    _routes["tunein"] = ([], "searched TuneIn")

    found = federated_browse.search_everything("nothing", targets=federated_browse.TARGETS)

    assert found.failed == []
    assert federated_browse.describe("nothing", found) == "Nothing found for nothing."


def test_one_loud_source_cannot_bury_the_others(_routes: dict) -> None:
    many = [leaf(_station(f"Station {n}", f"http://s{n}")) for n in range(500)]
    _routes["tunein"] = (many, "")

    found = federated_browse.search_everything("s", targets=federated_browse.TARGETS)

    assert len(found.rows) == federated_browse.PER_SOURCE_LIMIT


def test_an_empty_query_asks_nobody(_routes: dict) -> None:
    _routes["tunein"] = ([leaf(_station("Jazz", "http://a"))], "")

    found = federated_browse.search_everything("   ")

    assert found.total == 0
    assert found.asked == []


def test_the_podcast_narrowing_comes_from_the_source_table() -> None:
    # "Search for a Podcast..." must not carry its own list of sources: a new
    # podcast directory added to TARGETS has to reach it for free.
    podcast_targets = federated_browse.targets_of_type("Podcast")

    assert podcast_targets
    assert all(t.type_label == "Podcast" for t in podcast_targets)
    assert set(podcast_targets) <= {federated_browse.STATIONS, *federated_browse.TARGETS}


def test_safe_mode_says_so_once_rather_than_per_source(_routes: dict) -> None:
    found = federated_browse.search_everything("x", safe_mode=True)

    said = federated_browse.describe("x", found, safe_mode=True)
    assert said.count("Safe Mode") == 1
    assert "offline station catalog" in said
