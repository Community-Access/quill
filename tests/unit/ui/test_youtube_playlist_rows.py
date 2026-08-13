"""Tests for how a YouTube playlist row reads aloud.

The row label is the whole accessibility story for the picker: it is a plain
ListBox, so what a screen reader says *is* this string. Durations are spelled in
words because "5:31" read verbatim is ambiguous unless the reader already knows
it is a time.
"""

from quill.core.radio.youtube import YouTubePlaylistEntry
from quill.ui.radio.youtube_playlist_dialog import describe_entry


def test_a_row_leads_with_its_position_and_title() -> None:
    entry = YouTubePlaylistEntry(page_url="https://x", title="Introducing layers")
    assert describe_entry(3, entry).startswith("3. Introducing layers")


def test_minutes_and_seconds_are_spelled_out() -> None:
    entry = YouTubePlaylistEntry(page_url="https://x", title="A", duration_ms=331_000)
    assert "5 minutes 31 seconds" in describe_entry(1, entry)


def test_a_long_video_reads_in_hours() -> None:
    entry = YouTubePlaylistEntry(page_url="https://x", title="A", duration_ms=3_725_000)
    label = describe_entry(1, entry)
    assert "1 hour" in label
    assert "2 minutes" in label


def test_a_single_minute_is_not_pluralised() -> None:
    entry = YouTubePlaylistEntry(page_url="https://x", title="A", duration_ms=61_000)
    assert "1 minute 1 seconds" in describe_entry(1, entry)


def test_a_short_video_reads_in_seconds_only() -> None:
    entry = YouTubePlaylistEntry(page_url="https://x", title="A", duration_ms=42_000)
    assert "42 seconds" in describe_entry(1, entry)


def test_an_unknown_duration_is_simply_omitted() -> None:
    """Better to say nothing than to announce a misleading zero."""
    entry = YouTubePlaylistEntry(page_url="https://x", title="A")
    label = describe_entry(1, entry)
    assert "second" not in label
    assert label == "1. A"


def test_the_uploader_is_included_when_known() -> None:
    entry = YouTubePlaylistEntry(page_url="https://x", title="A", uploader="3Blue1Brown")
    assert "3Blue1Brown" in describe_entry(1, entry)


def test_an_untitled_entry_falls_back_to_its_link() -> None:
    """A row must never read as a bare number with nothing after it."""
    entry = YouTubePlaylistEntry(page_url="https://youtu.be/abc", title="   ")
    assert describe_entry(2, entry) == "2. https://youtu.be/abc"
