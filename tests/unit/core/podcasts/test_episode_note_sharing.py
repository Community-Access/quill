"""Sharing one timestamped note as text (x.md item 11).

Item 9 applied to a note: what makes a bookmark worth handing to somebody is
not the note's words but *where in what* they point, so the episode, the show,
the timestamp, the note and the link travel together. The note text pasted
alone is a fragment nobody can act on.
"""

from __future__ import annotations

from quill.core.podcasts.episode_notes import (
    EpisodeNote,
    format_note_for_sharing,
    format_timestamp,
)


def _note(position_ms: int = 754_000, text: str = "The bit about beeswax") -> EpisodeNote:
    return EpisodeNote(
        note_id="n1",
        show_id="show-1",
        episode_guid="ep-1",
        position_ms=position_ms,
        text=text,
        created_at="2026-08-13T09:00:00+00:00",
    )


def test_a_full_note_carries_everything_needed_to_act_on_it() -> None:
    text = format_note_for_sharing(
        _note(),
        show_title="The Daily",
        episode_title="Episode One",
        audio_url="https://example.com/ep1.mp3",
    )

    assert text == (
        "Episode One -- The Daily\nAt 12:34: The bit about beeswax\nhttps://example.com/ep1.mp3"
    )


def test_an_hour_long_position_reads_as_hours() -> None:
    text = format_note_for_sharing(_note(position_ms=3_754_000), episode_title="Long One")
    assert "At 1:02:34:" in text


def test_a_note_with_no_context_still_copies() -> None:
    """A note whose show has since been unsubscribed must copy rather than
    raise -- and absent parts are left out, not shown as empty labels."""
    text = format_note_for_sharing(_note())

    assert text == "At 12:34: The bit about beeswax"
    assert "--" not in text
    assert not text.startswith("\n")


def test_a_missing_show_title_does_not_leave_a_dangling_separator() -> None:
    text = format_note_for_sharing(_note(), episode_title="Episode One")
    assert text.splitlines()[0] == "Episode One"


def test_a_missing_episode_title_falls_back_to_the_show() -> None:
    text = format_note_for_sharing(_note(), show_title="The Daily")
    assert text.splitlines()[0] == "The Daily"


def test_a_blank_audio_url_adds_no_empty_line() -> None:
    text = format_note_for_sharing(_note(), episode_title="Episode One", audio_url="   ")
    assert text.splitlines() == ["Episode One", "At 12:34: The bit about beeswax"]


def test_an_empty_note_does_not_leave_trailing_whitespace() -> None:
    text = format_note_for_sharing(_note(text=""), episode_title="Episode One")
    assert text == "Episode One\nAt 12:34:"


def test_a_multi_line_note_keeps_its_lines() -> None:
    text = format_note_for_sharing(_note(text="First line\nSecond line"))
    assert text == "At 12:34: First line\nSecond line"


# -- the written timestamp ---------------------------------------------------


def test_the_timestamp_is_written_form_only() -> None:
    """Written down m:ss is unambiguous; spoken it is not, which is why every
    announcement says "12 minutes 34 seconds" instead."""
    assert format_timestamp(0) == "0:00"
    assert format_timestamp(5_000) == "0:05"
    assert format_timestamp(65_000) == "1:05"
    assert format_timestamp(3_600_000) == "1:00:00"


def test_a_negative_position_clamps_to_zero() -> None:
    assert format_timestamp(-5_000) == "0:00"
