"""Search has no memory in Cast -- until now (list.md 5.5).

Quill Radio keeps recent searches, so the query somebody runs weekly is one
arrow key away. Cast's Search Everywhere started from nothing every time.

The gap costs more than it sounds. "The episode about the harbour" is a search
somebody runs several times across a week, from a different place in the
library each time, and the query is the part they have to reconstruct from
memory on every attempt -- a typo means starting over.

Two rules make a list like this worth opening, and both are here:

* repeating a search **moves it up** rather than adding a second copy, and
* an empty search is **never** remembered.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts import search_history as sh
from quill.core.podcasts.history import PodcastHistory, load_history, save_history


def test_a_search_is_remembered() -> None:
    assert sh.remember((), "harbour") == ("harbour",)


def test_the_newest_search_is_first() -> None:
    """The order somebody wants: what I just did, then what I did before."""
    assert sh.remember(("harbour",), "jazz") == ("jazz", "harbour")


def test_running_a_search_again_moves_it_up_rather_than_repeating_it() -> None:
    """A list whose top five rows are one query five times has spent its whole
    length on one search."""
    entries = sh.remember(sh.remember(("harbour",), "jazz"), "harbour")

    assert entries == ("harbour", "jazz")


def test_the_same_intention_typed_twice_is_one_row() -> None:
    """Two rows a screen reader reads identically are worse than useless --
    they are indistinguishable, and one of them is a wasted arrow press."""
    entries = sh.remember(("Harbour",), "  harbour ")

    assert entries == ("harbour",)


def test_an_empty_search_is_never_remembered() -> None:
    """Clearing the box is how you start over, not a place to come back to."""
    for blank in ("", "   ", "\t"):
        assert sh.remember(("harbour",), blank) == ("harbour",)


def test_the_list_stops_at_a_length_somebody_can_arrow_through() -> None:
    entries: tuple[str, ...] = ()
    for index in range(40):
        entries = sh.remember(entries, f"search {index}")

    assert len(entries) == sh.MAX_RECENT_SEARCHES == 15
    assert entries[0] == "search 39"


def test_a_search_that_found_nothing_is_still_worth_keeping() -> None:
    """Often the most worth keeping: it is the one somebody will try again
    with different words."""
    assert "nothing at all" in sh.remember((), "nothing at all")


# -- the stored form ------------------------------------------------------------


def test_it_round_trips_through_json() -> None:
    entries = ("harbour", "jazz")

    assert sh.from_json(sh.to_json(entries)) == entries


def test_a_damaged_file_costs_the_history_and_not_the_app() -> None:
    """Forgiving in one direction only: a half-finished write should cost
    somebody their search list at worst, never their ability to open Cast."""
    assert sh.from_json(None) == ()
    assert sh.from_json("harbour") == ()
    assert sh.from_json([{"query": "harbour"}, 7, None, "jazz", "  ", "jazz"]) == ("jazz",)


def test_it_rides_the_history_file_the_played_list_already_uses(tmp_path: Path) -> None:
    """One file, so clearing the recently-played list clears this too. A
    second record of what somebody has been searching for, kept somewhere they
    did not know about, is the wrong answer for a list like this."""
    history = PodcastHistory()
    history.recent_searches = ("harbour", "jazz")
    save_history(tmp_path, history)

    assert (tmp_path / "podcast_history.json").is_file()
    assert load_history(tmp_path).recent_searches == ("harbour", "jazz")


def test_an_older_file_reads_as_no_searches(tmp_path: Path) -> None:
    save_history(tmp_path, PodcastHistory())
    store = tmp_path / "podcast_history.json"
    store.write_text(
        store.read_text(encoding="utf-8").replace('"recent_searches": [],', ""), encoding="utf-8"
    )

    assert load_history(tmp_path).recent_searches == ()


def test_nothing_here_touches_the_network() -> None:
    """This is a list of what somebody has been searching for. It stays on
    their machine, and the module is small enough to prove it by reading."""
    source = Path(sh.__file__).read_text(encoding="utf-8")

    for outbound in ("requests", "urllib", "http", "socket", "urlopen"):
        assert outbound not in source
