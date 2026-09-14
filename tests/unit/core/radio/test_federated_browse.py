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


# -- a website address is scanned, not searched for (issue #1491) ------------
#
# Pasting "oj991.com" into Search All Sources used to hand that text to every
# directory as a name query. Radio Browser matched the token "com" and the
# answer was 33 rows -- Cruisin92.com, STAR1079.com, ACCRA24.COM -- none of
# them the station, and the one thing that could have found it (the website
# scanner, already wired into the Find Stations search box) was never asked.


def _scan(monkeypatch: pytest.MonkeyPatch, candidates: list[tuple[str, str, str]]) -> list[str]:
    """Stub the scanner; returns the list that records what it was asked to scan."""
    from quill.core.radio import link_finder

    scanned: list[str] = []

    def fake_scan(url: str, *, safe_mode: bool = False) -> link_finder.PageScanResult:
        scanned.append(url)
        return link_finder.PageScanResult(
            page_title="OJ 99.1 WWOJ",
            favicon_url="",
            candidates=[
                link_finder.PageStreamCandidate(url=u, reason=r, label=lab)
                for u, r, lab in candidates
            ],
        )

    monkeypatch.setattr(link_finder, "scan_page_for_streams", fake_scan)
    return scanned


def test_a_url_is_scanned_for_streams_instead_of_searched_for(
    _routes: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes["rbgenre"] = (
        [leaf(_station("Cruisin92.com", "http://junk"))],
        "searched Radio Browser",
    )
    scanned = _scan(
        monkeypatch,
        [("https://ice42.securenetsystems.net/WWOJ", "stream from the station's player", "WWOJ")],
    )

    found = federated_browse.search_everything("oj991.com")

    assert scanned == ["oj991.com"]
    assert [row.label for row in found.rows] == ["WWOJ"]
    assert found.rows[0].station is not None
    assert found.rows[0].station.stream_url == "https://ice42.securenetsystems.net/WWOJ"
    # The directories are not asked at all: their answer to a hostname is noise.
    assert "Cruisin92.com" not in [row.label for row in found.rows]


def test_a_scanned_row_says_it_came_from_the_website(
    _routes: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _scan(monkeypatch, [("https://ice42.securenetsystems.net/WWOJ", "player stream", "WWOJ")])

    found = federated_browse.search_everything("oj991.com")

    assert found.rows[0].note.startswith("Station, Website")
    assert found.asked == ["Website"]
    assert federated_browse.describe("oj991.com", found) == "1 found for oj991.com: 1 station."


def test_a_candidate_with_no_label_still_names_itself(
    _routes: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The scanner's label is the anchor text, which is often empty. Falling
    # through to the page title beats a row called "" or the raw URL.
    _scan(monkeypatch, [("https://ice42.securenetsystems.net/WWOJ", "player stream", "")])

    found = federated_browse.search_everything("oj991.com")

    assert found.rows[0].label == "OJ 99.1 WWOJ"


def test_a_website_with_no_streams_says_so_rather_than_listing_the_directories(
    _routes: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes["rbgenre"] = ([leaf(_station("STAR1079.com", "http://junk"))], "searched Radio Browser")
    _scan(monkeypatch, [])

    found = federated_browse.search_everything("example.com")

    assert found.rows == []
    assert federated_browse.describe("example.com", found) == "Nothing found for example.com."


def test_an_unreachable_website_is_named_like_any_other_source(
    _routes: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.radio import link_finder

    def boom(url: str, *, safe_mode: bool = False) -> object:
        raise link_finder.LinkFinderError("That website could not be reached.")

    monkeypatch.setattr(link_finder, "scan_page_for_streams", boom)

    found = federated_browse.search_everything("oj991.com")

    assert found.rows == []
    # Named like any other unreachable source, carrying the error's own words.
    assert len(found.failed) == 1
    label, why = found.failed[0]
    assert label == "Website"
    assert "could not be reached" in why


def test_safe_mode_does_not_scan_a_website(_routes: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    scanned = _scan(monkeypatch, [("http://s", "r", "S")])

    found = federated_browse.search_everything("oj991.com", safe_mode=True)

    assert scanned == []
    assert found.rows == []
    assert found.failed and found.failed[0][0] == "Website"


def test_a_scoped_search_is_left_alone(_routes: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    # "Search for a Podcast..." passes its own targets. A URL there is still a
    # podcast search: scanning for radio streams would answer a question the
    # listener did not ask.
    scanned = _scan(monkeypatch, [("http://s", "r", "S")])
    _routes["apple"] = ([folder("appleshow:1", "A Show")], "searched Apple")

    found = federated_browse.search_everything(
        "oj991.com", targets=federated_browse.targets_of_type("Podcast")
    )

    assert scanned == []
    assert [row.label for row in found.rows] == ["A Show"]


def test_a_plain_name_query_is_never_scanned(
    _routes: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    scanned = _scan(monkeypatch, [("http://s", "r", "S")])
    _routes["rbgenre"] = ([leaf(_station("Jazz FM", "http://a"))], "searched Radio Browser")

    # catalog= anything non-None so the station route answers from the stub
    # rather than reaching for the live directory.
    found = federated_browse.search_everything("Jazz FM", catalog=object())

    assert scanned == []
    assert [row.label for row in found.rows] == ["Jazz FM"]
