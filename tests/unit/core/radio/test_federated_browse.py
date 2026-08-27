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


# --- speed: one wave, a deadline, and the three new directories --------------
# Reported 2026-08-26: "global search ... is very very slow right now."


def test_every_source_is_asked_at_the_same_moment() -> None:
    """Six workers over sixteen targets was three waves of the slowest service."""
    import threading

    from quill.core.radio import federated_browse as fb

    started = threading.Semaphore(0)
    hold = threading.Event()
    targets = tuple(fb.SearchTarget(f"s{i}", f"S{i}", "Station") for i in range(12))

    def _ask(target, _text, *, safe_mode, catalog):  # noqa: ARG001
        started.release()
        hold.wait(5)
        return [], ""

    original = fb._ask
    fb._ask = _ask
    try:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as runner:
            future = runner.submit(fb.search_everything, "jazz", targets=targets)
            # All twelve must be in flight before any of them is allowed to
            # finish; with a six-worker pool this deadlocks the test instead.
            for _ in targets:
                assert started.acquire(timeout=5)
            hold.set()
            future.result(timeout=10)
    finally:
        hold.set()
        fb._ask = original


def test_a_source_that_never_answers_does_not_hold_the_whole_search() -> None:
    from quill.core.radio import federated_browse as fb

    slow = fb.SearchTarget("slow", "Slow Directory", "Station")
    quick = fb.SearchTarget("quick", "Quick Directory", "Station")

    def _ask(target, _text, *, safe_mode, catalog):  # noqa: ARG001
        if target.seed_id == "slow":
            import time

            time.sleep(5)
        return [], ""

    original = fb._ask
    fb._ask = _ask
    try:
        found = fb.search_everything("jazz", targets=(quick, slow), deadline_seconds=0.5)
    finally:
        fb._ask = original

    # The quick one is in the answer; the slow one is *named*, not dropped in
    # silence -- a short list must never pass itself off as a complete one.
    assert "Quick Directory" in found.asked
    assert any(label == "Slow Directory" for label, _why in found.failed)
    assert any("did not answer" in why for _label, why in found.failed)


def test_the_three_new_directories_are_searched_from_the_tree_too() -> None:
    """Browsing a directory you cannot search from Search All Sources is half a source."""
    from quill.core.radio import federated_browse as fb

    seeds = {target.seed_id for target in fb.TARGETS}
    assert {"shoutcast", "live365", "radioparadise"} <= seeds


def test_each_of_them_has_a_fast_route_rather_than_a_crawl() -> None:
    from quill.core.radio import branch_find

    for kind in ("shoutcast", "live365", "radioparadise"):
        assert any(prefix == kind for prefix, _fn in branch_find._PREFIX_ROUTES)
