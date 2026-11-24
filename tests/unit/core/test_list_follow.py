"""Lists that stay still (FUX-06): the shared choice of row, row changes and words."""

from __future__ import annotations

import random

from quill.core.list_follow import change_rows, gone_sentence, hidden_sentence, land


def test_the_reader_lands_on_their_own_item_wherever_it_moved() -> None:
    landing = land(["c", "a", "b"], "b", previous=1)
    assert (landing.index, landing.kept) == (2, True)


def test_a_gone_item_lands_on_the_row_that_moved_into_its_place() -> None:
    landing = land(["a", "c", "d"], "b", previous=1)
    assert (landing.index, landing.kept) == (1, False)
    # The last row went: the new last row, not the top.
    assert land(["a", "b"], "c", previous=2).index == 1


def test_a_reader_on_nothing_is_not_told_anything_went() -> None:
    assert land(["a"], None, previous=-1).kept is True
    assert land([], "a", previous=0).index == -1


def _apply(old: list[str], new: list[str], pin: str | None = None) -> tuple[list[str], list[str]]:
    """Run change_rows on a list of (key, item) pairs; return keys and items."""
    rows = [(key, f"item-{key}") for key in old]
    counter = iter(range(1000))

    def insert(row: int, new_index: int) -> None:
        rows.insert(row, (new[new_index], f"new-{next(counter)}"))

    def update(row: int, new_index: int) -> None:
        assert rows[row][0] == new[new_index]

    change_rows(old, new, delete=rows.pop, insert=insert, update=update, pin=pin)
    return [key for key, _item in rows], [item for _key, item in rows]


def test_rows_that_stay_keep_their_item_and_only_arrivals_are_new() -> None:
    keys, items = _apply(["b", "d", "e"], ["a", "b", "c", "d", "e", "f"])
    assert keys == ["a", "b", "c", "d", "e", "f"]
    assert items[1] == "item-b" and items[3] == "item-d" and items[4] == "item-e"


def test_change_rows_reaches_any_order_from_any_order() -> None:
    rng = random.Random(6)
    for _ in range(200):
        old = rng.sample("abcdefghij", rng.randint(0, 10))
        new = rng.sample("abcdefghij", rng.randint(0, 10))
        assert _apply(old, new)[0] == new


def test_a_pinned_row_survives_any_reordering_as_the_same_item() -> None:
    rng = random.Random(9)
    for _ in range(200):
        old = rng.sample("abcdefghij", rng.randint(1, 10))
        pin = rng.choice(old)
        new = rng.sample("abcdefghij", rng.randint(0, 10))
        if pin not in new:
            new.insert(rng.randint(0, len(new)), pin)
        keys, items = _apply(old, new, pin)
        assert keys == new
        assert items[new.index(pin)] == f"item-{pin}"


def test_the_sentences_name_the_item_once_and_plainly() -> None:
    assert gone_sentence("Morning Edition") == "Morning Edition is no longer in the list."
    assert gone_sentence("  ") == "The item you were on is no longer in the list."
    assert hidden_sentence("WNYC") == "WNYC is not shown with this filter."
