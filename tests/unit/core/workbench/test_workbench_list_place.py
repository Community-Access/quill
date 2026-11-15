"""Where the Workbench list lands after a refill (rows read once, place kept). Wx-free."""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.workbench.list_place import landing_index, row_identity, same_cells


@dataclass
class _Row:
    url: str
    label: str = ""


def test_identity_is_by_the_items_address_not_its_words() -> None:
    assert row_identity(_Row("u1", "Unread: x")) == row_identity(_Row("u1", "Read: x"))
    assert row_identity(_Row("u1")) != row_identity(_Row("u2"))
    assert row_identity(object()) == ""


def test_landing_keeps_the_same_item_wherever_it_moved() -> None:
    old = [_Row("a"), _Row("b"), _Row("c")]
    new = [_Row("c"), _Row("a"), _Row("b", "now read")]
    assert landing_index(old, 1, new) == 2


def test_a_removed_item_lands_on_the_row_now_in_its_place() -> None:
    old = [_Row("a"), _Row("b"), _Row("c")]
    assert landing_index(old, 1, [_Row("a"), _Row("c")]) == 1
    assert landing_index(old, 2, [_Row("a"), _Row("b")]) == 1


def test_no_place_lands_on_the_first_row_and_empty_on_none() -> None:
    assert landing_index([], -1, [_Row("a")]) == 0
    assert landing_index([_Row("a")], 0, []) == -1


def test_same_cells() -> None:
    assert same_cells([["a", "1"]], [["a", "1"]])
    assert not same_cells([["a", "1"]], [["a", "2"]])
    assert not same_cells([["a"]], [["a"], ["b"]])
