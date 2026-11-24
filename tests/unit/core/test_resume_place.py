"""Reopening a document puts the cursor back in its sentence, or says it cannot (FUX-01).

The rule is :mod:`quill.core.resume_place`, shared by QUILL and QUILL Lite, and
the store is :class:`~quill.core.bookmarks.DocumentMemory`. QUILL's wiring is
``tests/unit/ui/test_main_frame_resume_place.py``; QUILL Lite's is in
``tests/unit/apps/test_lite_document_memory.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.bookmark_anchor import capture_anchor, locate_anchor, resolve_anchor
from quill.core.bookmarks import DOCUMENT_MEMORY_FILENAME, DocumentMemory
from quill.core.resume_place import (
    ResumedPlace,
    anchor_if_saved,
    lost_place_sentence,
    resume_place,
)

TEXT = "".join(f"Sentence {n} belongs to line {n} alone.\n" for n in range(30))


def test_locate_says_whether_the_text_was_found() -> None:
    anchor = capture_anchor(TEXT, TEXT.index("line 20"))

    assert locate_anchor("Added.\n" + TEXT, anchor) == (TEXT.index("line 20") + 7, True)
    gone = "nothing like it\n" * 30
    position, found = locate_anchor(gone, anchor)
    assert found is False
    assert position == resolve_anchor(gone, anchor)  # the old answer is unchanged


def test_an_unchanged_document_resumes_exactly() -> None:
    where = TEXT.index("line 9")
    assert resume_place(TEXT, where, capture_anchor(TEXT, where)) == ResumedPlace(where)


def test_a_lost_place_goes_to_the_start_of_its_line_and_is_marked() -> None:
    where = TEXT.index("line 9 alone")
    other = "".join(f"Different {n}.\n" for n in range(30))

    place = resume_place(other, where, capture_anchor(TEXT, where))

    assert place == ResumedPlace(other.index("Different 9."), lost=True)
    assert lost_place_sentence(other, place.position).endswith("line 10.")


def test_a_shorter_document_puts_a_lost_place_on_its_last_line() -> None:
    where = TEXT.index("line 25")
    place = resume_place("one\ntwo", where, capture_anchor(TEXT, where))
    assert place == ResumedPlace(4, lost=True)


def test_without_an_anchor_the_offset_is_used_as_before() -> None:
    assert resume_place(TEXT, 50, None) == ResumedPlace(50)
    assert resume_place(TEXT, 0, None) is None
    assert resume_place("short", 500, None) is None  # past the end is refused
    assert resume_place(TEXT, None, None) is None


def test_only_saved_text_gets_an_anchor() -> None:
    assert anchor_if_saved(TEXT, TEXT, 10) == capture_anchor(TEXT, 10)
    assert anchor_if_saved(TEXT, "older", 10) is None
    assert anchor_if_saved(TEXT, None, 10) is None


def test_the_store_round_trips_the_anchor_and_forgets_a_stale_one(tmp_path: Path) -> None:
    path = tmp_path / DOCUMENT_MEMORY_FILENAME
    store = DocumentMemory.load(path)
    key = store.key_for(tmp_path / "doc.txt")
    anchor = capture_anchor(TEXT, 40)

    store.set_last_position(key, 40, anchor=anchor)
    assert DocumentMemory.load(path).last_anchor(key) == anchor

    store.set_last_position(key, 41)  # no anchor: the old one described offset 40
    reread = DocumentMemory.load(path)
    assert reread.last_position(key) == 41
    assert reread.last_anchor(key) is None


def test_a_key_from_a_newer_build_is_kept(tmp_path: Path) -> None:
    """GATE-DATAFMT: going back a version must not erase what a newer one wrote."""
    path = tmp_path / DOCUMENT_MEMORY_FILENAME
    key = DocumentMemory.key_for(tmp_path / "doc.txt")
    path.write_text(
        json.dumps({key: {"bookmarks": {}, "last_position": 3, "selection_end": 9}}),
        encoding="utf-8",
    )

    store = DocumentMemory.load(path)
    store.set_last_position(key, 4)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved[key]["selection_end"] == 9
    assert saved[key]["last_position"] == 4


def test_an_emptied_file_is_left_at_its_start_without_a_word() -> None:
    """The reader says the document is blank; "line 1" would add nothing."""
    where = TEXT.index("line 9")
    assert resume_place("", where, capture_anchor(TEXT, where)) is None


def test_the_sentence_says_exactly_where_the_cursor_is() -> None:
    text = "one\ntwo\nthree\n"
    assert lost_place_sentence(text, text.index("three")) == (
        "The text where you left off has changed. The cursor is at the start of line 3."
    )
