"""Go To, in QUILL Cast (list.md 5.2).

Radio's "one key for every place" is a list the listener composes: the six
places they actually go, on one key each, in an order that never moves. Cast's
only "Go To" was ``podcasts.go_to_position``, which jumps to a *time inside an
episode* -- a different feature with the same two words, which is worse than
not having one, because somebody looking for the first finds the second.

The property the whole feature rests on is that **the numbering does not
move**. The Window menu does not answer this question precisely because it
renumbers. So the tests that matter are about what happens on upgrade and to a
damaged file, not about the happy path.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import go_to_menu
from quill.core.podcasts import go_to


def test_a_fresh_install_gets_the_first_ten() -> None:
    layout = go_to.default_layout()

    assert len(layout.order) == go_to.MAX_ENTRIES == 10
    assert [d.id for d in layout.ordered()] == list(go_to.DEFAULT_ORDER)


def test_the_menu_leads_with_where_the_work_happens() -> None:
    """A claim about how a podcast app is used, and the reason it is worth
    stating: position 1 is the one somebody presses without looking."""
    assert go_to.DEFAULT_ORDER[0] == "manager"
    assert go_to.DEFAULT_ORDER[1] == "continue"


def test_a_new_destination_lands_in_the_pool_not_in_the_menu() -> None:
    """The protection that makes fixed numbering possible. If a release could
    insert a place into the menu, every number after it would move, and the
    numbering is the entire value."""
    saved = go_to.GoToLayout(order=list(go_to.DEFAULT_ORDER), catalogue=go_to.DESTINATIONS)
    later = (*go_to.DESTINATIONS, go_to_menu.Destination("brand_new", "Brand New", "open_new"))

    repaired = go_to_menu.repair(go_to_menu.GoToLayout(order=list(saved.order), catalogue=later))

    assert [d.id for d in repaired.ordered()] == list(go_to.DEFAULT_ORDER)
    assert "brand_new" in repaired.available_ids()


def test_a_place_that_no_longer_exists_is_dropped_rather_than_raising() -> None:
    """A layout saved by a newer build must degrade to a working menu rather
    than to no app."""
    layout = go_to.repair(go_to.GoToLayout(order=["manager", "from_the_future", "queue"]))

    assert [d.id for d in layout.ordered()] == ["manager", "queue"]


def test_an_empty_layout_falls_back_to_the_default() -> None:
    assert go_to.repair(go_to.GoToLayout(order=[])).order == list(go_to.DEFAULT_ORDER)


def test_duplicates_are_collapsed() -> None:
    """Two rows that open the same place waste one of ten numbers."""
    layout = go_to.repair(go_to.GoToLayout(order=["manager", "manager", "queue"]))

    assert layout.order == ["manager", "queue"]


def test_the_menu_stops_at_ten_because_that_is_where_the_number_row_ends() -> None:
    order = [d.id for d in go_to.DESTINATIONS]
    assert len(order) > 10

    assert len(go_to.repair(go_to.GoToLayout(order=order)).order) == 10


def test_the_tenth_place_is_zero() -> None:
    assert go_to.position_key(0) == "1"
    assert go_to.position_key(8) == "9"
    assert go_to.position_key(9) == "0"
    assert go_to.position_key(10) == ""


def test_the_menu_cannot_be_emptied_and_says_why() -> None:
    """A sentence rather than a disabled button: a control that says only
    "no" is a control that has to be guessed at."""
    one = go_to.GoToLayout(order=["manager"], catalogue=go_to.DESTINATIONS)

    said = go_to.refusal_for_removing(one, "manager")

    assert "cannot be empty" in said
    assert go_to.refusal_for_removing(go_to.default_layout(), "manager") == ""


def test_a_full_menu_says_why_nothing_more_fits() -> None:
    said = go_to.refusal_for_adding(go_to.default_layout())

    assert "ten places" in said
    assert "eleventh key" in said


def test_it_saves_and_reloads(tmp_path: Path) -> None:
    go_to.save_layout(tmp_path, go_to.GoToLayout(order=["queue", "manager"]))

    assert (tmp_path / "cast-go-to.json").is_file()
    assert go_to.load_layout(tmp_path).order == ["queue", "manager"]


def test_a_missing_or_corrupt_file_is_the_default(tmp_path: Path) -> None:
    assert go_to.load_layout(tmp_path).order == list(go_to.DEFAULT_ORDER)

    (tmp_path / "cast-go-to.json").write_text("{ not json", encoding="utf-8")
    assert go_to.load_layout(tmp_path).order == list(go_to.DEFAULT_ORDER)


def test_the_two_apps_keep_separate_files(tmp_path: Path) -> None:
    """Same feature, different places. One file would mean arranging Cast's
    menu rearranged Radio's, and half the ids would be unknown on each side."""
    from quill.core.radio import go_to as radio_go_to

    go_to.save_layout(tmp_path, go_to.default_layout())
    radio_go_to.save_layout(tmp_path, radio_go_to.default_layout())

    assert (tmp_path / "cast-go-to.json").is_file()
    assert (tmp_path / "radio-go-to.json").is_file()
    assert go_to.load_layout(tmp_path).order != radio_go_to.load_layout(tmp_path).order


def test_every_place_names_a_door_and_a_title() -> None:
    for destination in go_to.DESTINATIONS:
        assert destination.id and destination.title and destination.opens
        assert destination.title[0].isupper()


def test_no_two_places_share_an_id_or_a_title() -> None:
    """Two rows a screen reader reads identically are two rows somebody has to
    press to tell apart."""
    ids = [d.id for d in go_to.DESTINATIONS]
    titles = [d.title for d in go_to.DESTINATIONS]

    assert len(ids) == len(set(ids))
    assert len(titles) == len(set(titles))


def test_the_rows_that_have_a_direct_key_show_it() -> None:
    """The popup teaches: somebody who uses Go To 1 for a month reads the
    direct key every time and eventually stops needing the popup. A shortcut
    that trains you out of itself is better than one that keeps you."""
    with_keys = [d for d in go_to.DESTINATIONS if d.key]

    assert with_keys
    for destination in with_keys:
        assert destination.key.startswith(("Ctrl", "Alt", "Shift", "F"))
