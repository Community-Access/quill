"""FUX-05: a recovery offer names the work, and every document's work is offered."""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

import pytest

from quill.core.autosave import autosave_document, snapshot_source
from quill.core.document import Document
from quill.core.recovery import begin_session
from quill.core.recovery_naming import (
    compare_with_saved,
    offer_sentence,
    snapshots_by_document,
    word_count,
    worth_offering,
)
from quill.core.recovery_triage import describe_plan, row_label, saved_comparison, triage


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


def _quiet_log(data_dir: Path) -> None:
    """A log with no error in it: what a power cut or a forced close leaves."""
    logs = data_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "quill.log").write_text("2026-11-24 10:00:00 INFO quill: idle\n", encoding="utf-8")


def test_autosave_notes_which_file_a_snapshot_is_of(data_dir: Path, tmp_path: Path) -> None:
    session = str(uuid4())
    saved = tmp_path / "chapter3.md"
    saved.write_text("old", encoding="utf-8")
    named = autosave_document(Document(text="new words", path=saved), session)
    untitled = autosave_document(Document(text="scratch", path=None), session)

    assert snapshot_source(named) == str(saved.resolve())
    assert snapshot_source(untitled) == ""


def test_a_snapshot_without_a_note_is_unknown_not_untitled(tmp_path: Path) -> None:
    snap = tmp_path / "abc-20261124T000000000000Z-000.snap"
    snap.write_text("words", encoding="utf-8")
    assert snapshot_source(snap) is None


def test_every_modified_document_is_offered_not_only_the_newest(
    data_dir: Path, tmp_path: Path
) -> None:
    """Before: only the newest snapshot of the session was ever offered."""
    previous, current = str(uuid4()), str(uuid4())
    one = tmp_path / "one.txt"
    two = tmp_path / "two.txt"
    one.write_text("saved one", encoding="utf-8")
    two.write_text("saved two", encoding="utf-8")
    begin_session(previous)
    autosave_document(Document(text="saved one and more", path=one), previous)
    autosave_document(Document(text="saved two and more", path=two), previous)
    _quiet_log(data_dir)

    offers = begin_session(current)

    assert sorted(Path(o.original_path or "").name for o in offers) == ["one.txt", "two.txt"]


def test_unsaved_work_is_offered_after_a_power_cut_with_a_clean_log(
    data_dir: Path, tmp_path: Path
) -> None:
    """Before: no error in the log meant no offer, and the work sat unreachable."""
    previous, current = str(uuid4()), str(uuid4())
    saved = tmp_path / "letter.txt"
    saved.write_text("Dear Sam,", encoding="utf-8")
    begin_session(previous)
    autosave_document(Document(text="Dear Sam, thank you for the book.", path=saved), previous)
    _quiet_log(data_dir)

    offers = begin_session(current)

    assert len(offers) == 1
    assert offers[0].original_path == str(saved.resolve())


def test_a_copy_identical_to_the_saved_file_is_not_offered(data_dir: Path, tmp_path: Path) -> None:
    previous, current = str(uuid4()), str(uuid4())
    saved = tmp_path / "done.txt"
    saved.write_bytes(b"all saved\r\n")
    begin_session(previous)
    autosave_document(Document(text="all saved\n", path=saved), previous)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs" / "quill.log").write_text("ERROR boom\n", encoding="utf-8")

    assert begin_session(current) == []


def test_only_the_newest_copy_of_each_document_is_kept(data_dir: Path, tmp_path: Path) -> None:
    session = str(uuid4())
    saved = tmp_path / "a.txt"
    first = autosave_document(Document(text="first", path=saved), session)
    os.utime(first, (time.time() - 60, time.time() - 60))
    second = autosave_document(Document(text="second", path=saved), session)

    assert snapshots_by_document(session) == [second]


def test_worth_offering_says_unknown_when_nothing_can_be_compared(tmp_path: Path) -> None:
    snap = tmp_path / "k-1.snap"
    snap.write_text("text", encoding="utf-8")
    word = tmp_path / "report.docx"
    word.write_bytes(b"PK\x03\x04binary")
    assert worth_offering(snap, None) is None
    assert worth_offering(snap, str(word)) is None
    assert worth_offering(snap, "") is True
    assert worth_offering(snap, str(tmp_path / "gone.txt")) is True


@pytest.mark.parametrize(
    ("copy", "saved", "expected"),
    [
        ("one two three four", "one two", "2 words more than the saved file"),
        ("one", "one two three", "2 words fewer than the saved file"),
        ("one two", "one two", "the same as the saved file"),
        ("one two", "three four", "as long as the saved file, with different words"),
    ],
)
def test_the_comparison_counts_words(tmp_path: Path, copy: str, saved: str, expected: str) -> None:
    path = tmp_path / "chapter.txt"
    path.write_text(saved, encoding="utf-8")
    assert compare_with_saved(copy, str(path), time.time() + 10) == expected


def test_the_comparison_says_when_the_saved_file_is_newer(tmp_path: Path) -> None:
    path = tmp_path / "chapter.txt"
    path.write_text("one", encoding="utf-8")
    said = compare_with_saved("one two", str(path), time.time() - 3600)
    assert said == "1 word more than the saved file, which was changed after this copy"


def test_a_word_file_is_compared_by_date_only(tmp_path: Path) -> None:
    path = tmp_path / "report.docx"
    path.write_bytes(b"PK\x03\x04")
    assert compare_with_saved("text", str(path), time.time() + 10) == ""
    assert compare_with_saved("text", str(path), time.time() - 3600) == (
        "the saved file was changed after this copy"
    )


def test_a_missing_file_is_said(tmp_path: Path) -> None:
    said = compare_with_saved("text", str(tmp_path / "moved.txt"), None)
    assert said == "the saved file is no longer there"


def test_the_offer_sentence_names_the_document_and_never_a_path() -> None:
    said = offer_sentence(
        r"C:\Users\someone\Documents\chapter3.md", "today at 2:14 PM", "1,200 words more"
    )
    assert said == "Unsaved changes to chapter3.md, autosaved today at 2:14 PM: 1,200 words more."
    assert offer_sentence("", "yesterday at 9:05 AM", "") == (
        "An untitled document that was never saved, autosaved yesterday at 9:05 AM."
    )
    assert "snapshot" not in offer_sentence(None, "today at 1:00 PM", "")


def test_word_count_counts_contractions_once() -> None:
    assert word_count("Don't stop, it's fine.") == 4


class _Slot:
    def __init__(self, content: Path, original: str) -> None:
        self.content_path = content
        self.original_path = original
        self.mode = "plain"

    @property
    def title(self) -> str:
        return Path(self.original_path).name if self.original_path else "Untitled"


def test_the_chooser_row_says_how_the_copy_differs_from_the_saved_file(tmp_path: Path) -> None:
    saved = tmp_path / "notes.txt"
    saved.write_text("alpha", encoding="utf-8")
    content = tmp_path / "slot.txt"
    content.write_text("alpha beta gamma", encoding="utf-8")
    os.utime(saved, (time.time() - 3600, time.time() - 3600))
    slot = _Slot(content, str(saved))

    assert saved_comparison(slot) == "2 words more than the saved file"
    assert row_label(slot).startswith(
        f"notes.txt  --  {saved}  --  2 words more than the saved file"
    )


def test_the_plan_says_the_file_on_disk_waits_for_a_save(tmp_path: Path) -> None:
    content = tmp_path / "slot.txt"
    content.write_text("words", encoding="utf-8")
    result = triage([_Slot(content, "")])
    plan = describe_plan(result, (True,))
    assert (
        "a file on disk changes only when you save it, and saving with Save As keeps the original"
        in plan
    )
