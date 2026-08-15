"""Marking and collecting pieces of a recording.

The cut has worked for a long time; this is the workflow around it. The rules
worth pinning are the safety ones -- **the source is never touched**, a mark is
never a commitment, and a too-short section is refused rather than written as a
file too short to be anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.audio.sections import (
    MIN_SECTION_MS,
    Section,
    SectionCollection,
    SectionMarks,
    describe_marks,
    save_sections,
    spoken_span,
)

_SOURCE = Path("interview.mp3")
_OTHER = Path("lecture.mp3")


def test_a_mark_can_be_set_in_either_order() -> None:
    # Somebody listening forward marks the start when they hear it begin and the
    # end when they hear it stop. Requiring both at once would mean knowing the
    # answer before listening.
    marks = SectionMarks()
    marks.mark_end(_SOURCE, 8_000)
    assert marks.section() is None
    marks.mark_start(_SOURCE, 4_000)
    section = marks.section()
    assert section is not None and (section.start_ms, section.end_ms) == (4_000, 8_000)


def test_marking_a_start_after_the_end_drops_the_stale_mark() -> None:
    # The pair would be inside out otherwise, and a section that ends before it
    # begins is not something to save with a warning -- it is not a section.
    marks = SectionMarks()
    marks.mark_end(_SOURCE, 4_000)
    marks.mark_start(_SOURCE, 9_000)
    assert marks.end_ms is None
    assert marks.section() is None


def test_marking_in_a_different_file_starts_a_fresh_pair() -> None:
    marks = SectionMarks()
    marks.mark_start(_SOURCE, 1_000)
    marks.mark_end(_OTHER, 9_000)
    # A section spanning two recordings would be meaningless.
    assert marks.start_ms is None
    assert marks.source == _OTHER


def test_a_section_shorter_than_the_floor_is_refused() -> None:
    marks = SectionMarks()
    marks.mark_start(_SOURCE, 1_000)
    marks.mark_end(_SOURCE, 1_000 + MIN_SECTION_MS - 1)
    assert marks.section() is None
    assert "too short to save" in describe_marks(marks)

    collection = SectionCollection()
    assert collection.add(Section(_SOURCE, 0, 10)) is False
    assert collection.sections == []


def test_every_description_is_words_never_a_timecode() -> None:
    marks = SectionMarks()
    assert describe_marks(marks) == "Nothing is marked."
    marks.mark_start(_SOURCE, 252_000)
    assert describe_marks(marks) == "Start marked at 4 minutes 12 seconds. No start yet.".replace(
        "No start", "No end"
    )
    marks.mark_end(_SOURCE, 330_000)
    said = describe_marks(marks)
    assert "4 minutes 12 seconds" in said
    assert "1 minute 18 seconds long" in said
    assert ":" not in said


def test_the_collection_reads_as_sentences_and_totals_itself() -> None:
    collection = SectionCollection()
    assert collection.describe() == "No sections collected yet."
    collection.add(Section(_SOURCE, 0, 60_000, "The good bit"))
    collection.add(Section(_SOURCE, 120_000, 150_000))
    assert collection.total_ms == 90_000
    assert "2 sections collected" in collection.describe()
    assert collection.row_label(0).startswith("1. The good bit, from")
    # An unlabelled section falls back to the file it came from, never a number.
    assert "interview.mp3" in collection.row_label(1)


def test_removing_and_clearing() -> None:
    collection = SectionCollection()
    collection.add(Section(_SOURCE, 0, 60_000))
    assert collection.remove(5) is None  # out of range is not an error
    assert collection.remove(0) is not None
    assert collection.sections == []
    collection.add(Section(_SOURCE, 0, 60_000))
    collection.clear()
    assert collection.total_ms == 0


def test_spoken_span_names_both_ends_and_the_length() -> None:
    said = spoken_span(Section(_SOURCE, 60_000, 150_000))
    assert said == "from 1 minute to 2 minutes 30 seconds, 1 minute 30 seconds long"


def test_saving_nothing_is_refused_rather_than_writing_an_empty_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no sections"):
        save_sections(SectionCollection(), tmp_path / "out.mp3", work_dir=tmp_path / "work")


def test_saving_never_writes_to_the_source(tmp_path: Path, monkeypatch) -> None:
    # The one rule that cannot be got wrong: there is no undo for a destructive
    # edit of the only copy of a recording, so there is no destructive edit.
    source = tmp_path / "interview.mp3"
    source.write_bytes(b"original audio")
    written: list[tuple[Path, Path]] = []

    def _fake_trim(src: Path, out: Path, *, start_ms: int, end_ms: int) -> Path:
        written.append((src, out))
        out.write_bytes(b"cut")
        return out

    import quill.core.speech.audio_edit as audio_edit

    monkeypatch.setattr(audio_edit, "trim_file", _fake_trim)

    collection = SectionCollection()
    collection.add(Section(source, 0, 60_000))
    destination = tmp_path / "out.mp3"
    save_sections(collection, destination, work_dir=tmp_path / "work")

    assert source.read_bytes() == b"original audio"
    assert all(out != source for _src, out in written)
    assert destination.exists()
