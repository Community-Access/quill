"""A-Z until you move one, then exactly as you left it.

The rule Jeff asked for on 2026-08-25: *"the default being sorted in A-Z order
even if they add them out of order, then if they move any keep those stuck in
position"*. Two promises that pull against each other, so each is pinned here.
"""

from __future__ import annotations

from quill.core.podcasts.pick_list import AZ, MANUAL, PickList


def _picks(*names: str) -> PickList:
    return PickList(key=str, items=names)


def _names(picks: PickList) -> list[str]:
    return list(picks.items)


def test_adding_out_of_order_still_reads_in_order() -> None:
    """Choosing what, not where: nobody should have to add alphabetically."""
    picks = PickList(key=str)
    picks.add("Zoom Call")
    picks.add("ACB Advocacy Update")
    picks.add("Marketplace")

    assert _names(picks) == ["ACB Advocacy Update", "Marketplace", "Zoom Call"]


def test_sorting_is_case_insensitive() -> None:
    picks = PickList(key=str)
    for name in ("banana", "Apple", "cherry"):
        picks.add(name)

    assert _names(picks) == ["Apple", "banana", "cherry"]


def test_the_same_show_cannot_be_chosen_twice() -> None:
    picks = _picks("ACB Community")

    assert picks.add("ACB Community") is False
    assert len(picks) == 1


def test_add_all_reports_how_many_were_new() -> None:
    """A verb that touches many rows says how many (GATE-BULK-COUNT)."""
    picks = _picks("ACB Community")

    added = picks.add_all(["ACB Community", "ACB Events", "ACB Focus: Advocacy"])

    assert added == 2
    assert len(picks) == 3


def test_moving_one_switches_the_list_to_manual() -> None:
    picks = _picks("Alpha", "Bravo", "Charlie")
    assert picks.order == AZ

    picks.move(2, -1)

    assert picks.order == MANUAL
    assert _names(picks) == ["Alpha", "Charlie", "Bravo"]


def test_a_show_moved_stays_put_when_more_are_added() -> None:
    """The whole point of the second rule: re-sorting around somebody who has
    just said where they want something is the app overruling them."""
    picks = _picks("Alpha", "Bravo", "Charlie")
    picks.move(2, -2)  # Charlie to the top
    assert _names(picks) == ["Charlie", "Alpha", "Bravo"]

    picks.add("Aardvark")

    assert _names(picks) == ["Charlie", "Alpha", "Bravo", "Aardvark"]


def test_moving_up_from_the_top_is_a_no_op_but_still_ends_az() -> None:
    """Clamped, not wrapped -- Move Up on the first row must not jump to the
    bottom. It still switches to manual: the reader engaged with the order."""
    picks = _picks("Alpha", "Bravo")

    landed = picks.move(0, -1)

    assert landed == 0
    assert _names(picks) == ["Alpha", "Bravo"]
    assert picks.order == MANUAL


def test_moving_down_from_the_bottom_is_clamped_too() -> None:
    picks = _picks("Alpha", "Bravo")

    assert picks.move(1, 1) == 1
    assert _names(picks) == ["Alpha", "Bravo"]


def test_move_returns_where_it_landed_so_the_cursor_can_follow() -> None:
    """A reorder that leaves the cursor behind makes the next press move the
    wrong row."""
    picks = _picks("Alpha", "Bravo", "Charlie")

    assert picks.move(0, 1) == 1


def test_removing_does_not_end_az() -> None:
    """Taking something out expresses no opinion about where the rest belong."""
    picks = _picks("Alpha", "Bravo", "Charlie")

    assert picks.remove_at(1) == "Bravo"
    assert picks.order == AZ

    picks.add("Aardvark")
    assert _names(picks) == ["Aardvark", "Alpha", "Charlie"]


def test_removing_out_of_range_says_so_rather_than_raising() -> None:
    picks = _picks("Alpha")

    assert picks.remove_at(5) is None
    assert picks.remove_at(-1) is None
    assert len(picks) == 1


def test_resort_is_the_way_back_from_manual() -> None:
    picks = _picks("Alpha", "Bravo", "Charlie")
    picks.move(2, -2)

    picks.resort()

    assert picks.order == AZ
    assert _names(picks) == ["Alpha", "Bravo", "Charlie"]


def test_a_list_restored_as_manual_is_not_re_sorted_on_construction() -> None:
    """Reopening the picker must not undo an arrangement already saved."""
    picks = PickList(key=str, items=["Charlie", "Alpha"], order=MANUAL)

    assert list(picks.items) == ["Charlie", "Alpha"]


def test_an_unknown_order_falls_back_to_az_rather_than_trusting_it() -> None:
    picks = PickList(key=str, items=["Charlie", "Alpha"], order="sideways")

    assert picks.order == AZ
    assert list(picks.items) == ["Alpha", "Charlie"]


def test_the_key_is_what_identifies_a_duplicate_not_the_object() -> None:
    """Shows are compared by feed URL in the picker, not by title."""
    picks = PickList(key=lambda show: show["feed"])
    picks.add({"feed": "https://example.com/a", "title": "One name"})

    assert picks.add({"feed": "https://example.com/a", "title": "Renamed"}) is False
    assert len(picks) == 1
