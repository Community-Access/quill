"""Find Stations remembers the searches you ran, as whole queries.

Find Stations remembered which sources it searched and which Source facet you
filtered by, on the stated principle that a preference you re-set every time is
not a preference -- and remembered nothing about the searches themselves.

The trap these guard is that a search is not a string. Name, tag and country
compose, so *jazz in France* and *jazz in Brazil* are different searches, and a
history that kept only "jazz" would hand back whichever one it happened to
store.
"""

from __future__ import annotations

from quill.core.radio.search_history import (
    MAX_RECENT_SEARCHES,
    SearchQuery,
    from_json,
    remember,
    to_json,
)


def test_a_search_is_the_whole_triple_not_just_the_name() -> None:
    france = SearchQuery(name="jazz", country="France")
    brazil = SearchQuery(name="jazz", country="Brazil")
    entries = remember(remember((), france), brazil)
    # Both survive: they are different searches that share a name.
    assert entries == (brazil, france)


def test_the_newest_search_comes_first() -> None:
    entries = remember(remember((), SearchQuery(name="first")), SearchQuery(name="second"))
    assert [entry.name for entry in entries] == ["second", "first"]


def test_repeating_a_search_moves_it_up_rather_than_duplicating_it() -> None:
    entries = (SearchQuery(name="jazz"), SearchQuery(name="blues"), SearchQuery(name="folk"))
    updated = remember(entries, SearchQuery(name="folk"))
    assert [entry.name for entry in updated] == ["folk", "jazz", "blues"]
    assert len(updated) == 3


def test_case_and_whitespace_do_not_make_a_second_entry() -> None:
    # "Jazz " and "jazz" are one intention typed twice, and two rows a screen
    # reader reads identically are indistinguishable, not merely untidy.
    updated = remember((SearchQuery(name="jazz"),), SearchQuery(name="  Jazz "))
    assert len(updated) == 1
    assert updated[0].name == "  Jazz "  # the newest spelling wins


def test_an_empty_search_is_never_remembered() -> None:
    entries = (SearchQuery(name="jazz"),)
    assert remember(entries, SearchQuery()) == entries
    assert remember(entries, SearchQuery(name="   ")) == entries


def test_the_list_is_capped() -> None:
    entries: tuple[SearchQuery, ...] = ()
    for index in range(MAX_RECENT_SEARCHES + 5):
        entries = remember(entries, SearchQuery(name=f"query {index}"))
    assert len(entries) == MAX_RECENT_SEARCHES
    # The cap drops the oldest, not the newest.
    assert entries[0].name == f"query {MAX_RECENT_SEARCHES + 4}"


def test_labels_name_the_field_each_value_came_from() -> None:
    # "blues" is a plausible station name as well as a plausible tag, so a bare
    # join ("jazz, blues, France") leaves the listener guessing.
    assert SearchQuery(name="jazz", tag="blues", country="France").label() == (
        "jazz, tagged blues, in France"
    )
    assert SearchQuery(name="jazz").label() == "jazz"
    assert SearchQuery(tag="blues").label() == "Tagged blues"
    assert SearchQuery(country="France").label() == "in France"
    assert SearchQuery().label() == "Empty search"


def test_a_round_trip_through_json_keeps_every_field() -> None:
    entries = (
        SearchQuery(name="jazz", tag="blues", country="France"),
        SearchQuery(name="talk"),
    )
    assert from_json(to_json(entries)) == entries


def test_a_damaged_history_costs_the_history_and_not_the_dialog() -> None:
    # A half-finished write must never stop Find Stations opening.
    assert from_json(None) == ()
    assert from_json("not a list") == ()
    assert from_json([1, "two", None]) == ()
    assert from_json([{"name": 5, "tag": [], "country": {}}]) == ()


def test_reading_back_drops_duplicates_and_empties_it_should_never_have_held() -> None:
    raw = [
        {"name": "jazz"},
        {"name": "JAZZ "},  # the same search, stored twice by an older build
        {"name": "", "tag": "", "country": ""},
        {"name": "folk"},
    ]
    assert [entry.name for entry in from_json(raw)] == ["jazz", "folk"]


def test_reading_back_honors_the_cap() -> None:
    raw = [{"name": f"query {index}"} for index in range(MAX_RECENT_SEARCHES + 10)]
    assert len(from_json(raw)) == MAX_RECENT_SEARCHES
