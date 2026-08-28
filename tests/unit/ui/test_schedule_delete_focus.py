"""Deleting a scheduled recording leaves you where you were (#1461).

Reported against Quill Radio 2.1.2: *"focus jumps back to the top of the list
after deleting a scheduled item I no longer need."* The remove handler rebuilt
the list without naming a row to keep, and a rebuild with no ``keep_id``
selects row 0. With focus still in the list -- Delete does the same thing the
Remove button does -- nothing announces that the position moved, so the next
Down arrow re-reads a schedule already dealt with, and a listener deleting
three stale entries walks the whole list three times.

``row_after_delete`` is the decision, pulled out of the handler so it can be
tested without a wx main loop: the row that took the deleted one's place.
"""

from __future__ import annotations

from quill.ui.radio.schedule_recording_dialog import row_after_delete


def test_deleting_the_middle_keeps_the_position() -> None:
    """Five entries, delete the third: you are on the new third."""
    assert row_after_delete(2, 4) == 2


def test_deleting_the_first_stays_at_the_top() -> None:
    assert row_after_delete(0, 4) == 0


def test_deleting_the_last_falls_back_to_the_new_last() -> None:
    """There is no row 4 in a four-row list; land on the end, not the top."""
    assert row_after_delete(4, 4) == 3


def test_deleting_the_only_entry_selects_nothing() -> None:
    assert row_after_delete(0, 0) is None


def test_a_nonsense_index_still_lands_inside_the_list() -> None:
    assert row_after_delete(-1, 3) == 0
    assert row_after_delete(99, 3) == 2


def test_the_handler_uses_it() -> None:
    """The bug was the handler refreshing with no keep_id; pin the cure."""
    import pathlib

    source = (
        pathlib.Path(__file__).resolve().parents[3]
        / "quill"
        / "ui"
        / "radio"
        / "schedule_recording_dialog.py"
    ).read_text(encoding="utf-8")
    remove_handler = source.split("def _on_remove_click(")[1].split("\n    def ")[0]
    assert "row_after_delete(" in remove_handler
    assert "self._refresh_list(keep_id=neighbour_id)" in remove_handler
    assert "self._refresh_list()" not in remove_handler
