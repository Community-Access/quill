"""FUX-02: a transcript or show notes handed to QUILL says where it came from."""

from __future__ import annotations

from pathlib import Path

from quill.core import editor_handoff
from quill.core.podcasts.transcripts import TranscriptCue


def _cues() -> list[TranscriptCue]:
    return [
        TranscriptCue(start_ms=0, end_ms=1000, text="Welcome."),
        TranscriptCue(start_ms=1000, end_ms=2000, text="   "),
        TranscriptCue(start_ms=750_000, end_ms=760_000, text="The part worth keeping."),
        TranscriptCue(start_ms=760_000, end_ms=770_000, text="Goodbye."),
    ]


def test_a_new_name_is_used_as_it_is(tmp_path: Path) -> None:
    assert editor_handoff.destination(tmp_path, "Show - One.md", "x") == tmp_path / "Show - One.md"


def test_the_same_document_sent_again_reopens_the_first_copy(tmp_path: Path) -> None:
    (tmp_path / "Show - One.md").write_text("same", encoding="utf-8")
    assert editor_handoff.destination(tmp_path, "Show - One.md", "same") == (
        tmp_path / "Show - One.md"
    )


def test_a_changed_copy_or_a_duplicate_name_is_never_written_over(tmp_path: Path) -> None:
    (tmp_path / "Show - One.md").write_text("edited by you", encoding="utf-8")
    (tmp_path / "Show - One (2).md").write_text("another episode", encoding="utf-8")
    assert editor_handoff.destination(tmp_path, "Show - One.md", "fresh") == (
        tmp_path / "Show - One (3).md"
    )


def test_the_document_names_the_app_the_moment_and_the_way_back() -> None:
    text, line = editor_handoff.transcript_document(
        _cues(),
        caret_index=2,
        source_app="QUILL Cast",
        detail="timestamps",
        show="The Show",
        episode="Episode 9",
    )
    lines = text.splitlines()
    assert lines[0] == "# Episode 9"
    assert "*The Show*" in lines
    assert any(
        row.startswith("Sent from QUILL Cast at 12:30 in the audio.") and "Enter" in row
        for row in lines
    )
    # The cursor goes to the line that was being read, in the document itself.
    assert line is not None and lines[line - 1] == "(12:30) The part worth keeping."


def test_bookmarks_travel_with_the_transcript_by_time() -> None:
    text, line = editor_handoff.transcript_document(
        _cues(),
        caret_index=0,
        source_app="QUILL Cast",
        bookmarks=[(760_000, "the goodbye"), (750_000, "")],
        detail="plain",
        episode="Episode 9",
    )
    lines = text.splitlines()
    marks = lines.index("## Your bookmarks")
    assert lines[marks + 2 : marks + 4] == ["- 12:30", "- 12:40: the goodbye"]
    assert "## Transcript" in lines
    assert line is not None and lines[line - 1] == "Welcome."


def test_a_caret_on_no_line_opens_at_the_top_and_claims_no_moment() -> None:
    text, line = editor_handoff.transcript_document(
        _cues(), caret_index=-1, source_app="Quill Radio", episode="A video"
    )
    assert line is None
    assert "Sent from Quill Radio. To hear any line again" in text
    # The transcript always has its heading, for heading navigation.
    assert "## Transcript" in text.splitlines()


def test_show_notes_name_the_episode_the_show_and_the_app() -> None:
    text = editor_handoff.text_document(
        "Guests\nJane.", kind="show notes", title="Thursday", show="The Daily", source_app="QUILL"
    )
    assert text.splitlines()[:6] == [
        "# Thursday",
        "",
        "*The Daily*",
        "",
        "Show notes, from QUILL.",
        "",
    ]
    assert text.endswith("Guests\nJane.\n")


def test_file_names_say_what_they_are() -> None:
    name = editor_handoff.document_filename
    assert name(kind="transcript", title="Ep: 1?", show="Show") == "Show - Ep 1.md"
    assert name(kind="show notes", title="Ep 1", show="Show") == "Show - Ep 1 show notes.md"


def test_a_two_line_caption_does_not_put_the_cursor_early() -> None:
    cues = [
        TranscriptCue(start_ms=0, end_ms=1000, text="First line\nof a caption."),
        TranscriptCue(start_ms=5_000, end_ms=6_000, text="Where you were."),
    ]
    text, line = editor_handoff.transcript_document(
        cues, caret_index=1, source_app="QUILL Cast", detail="plain", episode="E"
    )
    assert line is not None and text.splitlines()[line - 1] == "Where you were."
