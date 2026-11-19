"""The arithmetic under "lists that stay still" (FUX-06): which row goes at the top."""

from __future__ import annotations

from quill.ui.list_stay_still import NO_ANCHOR, RowAnchor, kept_top


def test_rows_inserted_above_move_the_view_down_by_as_many() -> None:
    # The reader was on row 5, two lines below the top (row 3); three rows
    # arrived above, so the episode is row 8 and the top becomes row 6.
    assert kept_top(RowAnchor(index=5, top=3, visible=True), 8, count=40) == 6


def test_rows_removed_above_move_the_view_up() -> None:
    assert kept_top(RowAnchor(index=5, top=3, visible=True), 4, count=40) == 2


def test_the_view_never_scrolls_past_the_ends() -> None:
    assert kept_top(RowAnchor(index=5, top=0, visible=True), 2, count=40) == 0
    assert kept_top(RowAnchor(index=1, top=0, visible=True), 90, count=10) == 9


def test_no_anchor_means_no_kept_line() -> None:
    assert kept_top(NO_ANCHOR, 4, count=40) == -1
    assert kept_top(RowAnchor(index=2, top=0, visible=True), 2, count=0) == -1
