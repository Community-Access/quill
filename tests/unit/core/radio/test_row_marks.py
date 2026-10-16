"""Mark many rows, then delete them with one question (xradio2 4.10)."""

from __future__ import annotations

from quill.core.radio.row_marks import (
    RowMarks,
    delete_question,
    deleted_sentence,
    landing_after,
    marked_label,
)


def test_toggle_marks_then_unmarks_and_counts() -> None:
    marks = RowMarks()
    assert marks.toggle("a") is True
    assert marks.toggle_sentence(True) == "Marked. 1 marked."
    assert marks.toggle("b") is True
    assert len(marks) == 2
    assert marks.toggle("a") is False
    assert marks.toggle_sentence(False) == "Unmarked. 1 marked."
    assert marks.keys == ["b"]


def test_unmarking_the_last_says_nothing_is_marked() -> None:
    marks = RowMarks()
    marks.toggle("a")
    marks.toggle("a")
    assert marks.toggle_sentence(False) == "Unmarked. Nothing marked."


def test_an_empty_key_is_never_marked() -> None:
    marks = RowMarks()
    assert marks.toggle("") is False
    assert len(marks) == 0


def test_marks_on_rows_that_went_away_are_forgotten() -> None:
    marks = RowMarks()
    for key in ("a", "b", "c"):
        marks.toggle(key)
    marks.keep_only(["a", "c", "d"])
    assert marks.keys == ["a", "c"]


def test_the_question_and_the_answer_both_say_how_many() -> None:
    assert delete_question(5, "station") == "Delete 5 stations?"
    assert delete_question(1, "station") == "Delete 1 station?"
    assert deleted_sentence(5, "station") == "Deleted 5 stations."
    assert deleted_sentence(4, "recording", failed=1) == (
        "Deleted 4 recordings. 1 recording could not be deleted."
    )


def test_a_marked_row_reads_marked() -> None:
    assert marked_label("WXYZ", True) == "WXYZ (marked)"
    assert marked_label("WXYZ", False) == "WXYZ"


def test_the_cursor_lands_on_a_survivor() -> None:
    order = ["a", "b", "c", "d", "e"]
    assert landing_after(order, "a", ["b", "c"]) == "a"
    assert landing_after(order, "b", ["b", "c"]) == "d"
    assert landing_after(order, "e", ["d", "e"]) == "c"
    assert landing_after(order, None, ["a"]) == "b"
    assert landing_after(order, "a", order) is None
