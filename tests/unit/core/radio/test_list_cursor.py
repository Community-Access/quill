"""Where the cursor goes after a delete -- one answer, two managers.

Both of Quill Radio's list managers got this wrong, in opposite directions:
Recordings left no selection at all (it restored by identity, and a deleted row
has none), and Favorites fell through to "select the first item", so deleting
the fortieth favourite read out the first with focus still in the tree.
"""

from __future__ import annotations

from quill.core.radio.list_cursor import index_after_removal, neighbour_key


def test_the_cursor_lands_on_the_row_that_took_its_place() -> None:
    assert index_after_removal(3, 10) == 3


def test_deleting_the_last_row_lands_on_the_new_last_row() -> None:
    assert index_after_removal(9, 9) == 8


def test_an_empty_list_is_a_different_fact_from_row_zero() -> None:
    # Worth saying out loud rather than leaving as a silent no-op.
    assert index_after_removal(0, 0) is None
    assert index_after_removal(5, 0) is None


def test_a_negative_index_does_not_walk_off_the_front() -> None:
    # GetFirstSelected returns -1 for "nothing selected".
    assert index_after_removal(-1, 4) == 0


def test_the_tree_lands_on_the_next_item() -> None:
    assert neighbour_key(["a", "b", "c"], "b") == "c"


def test_the_tree_lands_on_the_previous_item_when_the_last_one_goes() -> None:
    assert neighbour_key(["a", "b", "c"], "c") == "b"


def test_removing_the_only_item_has_nowhere_to_land() -> None:
    assert neighbour_key(["a"], "a") is None


def test_an_unknown_key_asks_for_nothing_rather_than_guessing() -> None:
    assert neighbour_key(["a", "b"], "z") is None
