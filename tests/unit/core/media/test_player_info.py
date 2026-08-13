"""Unit tests for the reviewable player-information report."""

from __future__ import annotations

from quill.core.media.player_info import (
    PlayerInfo,
    format_duration,
    format_speed,
    percent_complete,
    player_info_lines,
    player_info_summary,
    player_info_text,
    spoken_duration,
)


def test_format_duration_under_an_hour() -> None:
    assert format_duration(4 * 60_000 + 11_000) == "4:11"


def test_format_duration_over_an_hour_pads_minutes() -> None:
    assert format_duration((62 * 60 + 3) * 1000) == "1:02:03"


def test_format_duration_of_nothing() -> None:
    assert format_duration(0) == "0:00"
    assert format_duration(-5) == "0:00"


def test_spoken_duration_reads_as_words() -> None:
    assert spoken_duration((62 * 60 + 3) * 1000) == "1 hour 2 minutes 3 seconds"
    assert spoken_duration(60_000) == "1 minute"
    assert spoken_duration(0) == "0 seconds"


def test_percent_complete() -> None:
    assert percent_complete(30_000, 120_000) == 25
    assert percent_complete(0, 120_000) == 0
    assert percent_complete(30_000, 0) == 0
    assert percent_complete(999_000, 120_000) == 100


def test_format_speed_calls_one_normal() -> None:
    assert format_speed(1.0) == "Normal"
    assert format_speed(1.25) == "1.25x"
    assert format_speed(2.0) == "2x"


def _info(**fields: object) -> PlayerInfo:
    base = {
        "title": "Episode 12",
        "collection": "A Podcast",
        "position_ms": 60_000,
        "duration_ms": 300_000,
    }
    base.update(fields)
    return PlayerInfo(**base)  # type: ignore[arg-type]


def test_report_covers_the_basics() -> None:
    lines = player_info_lines(_info())
    assert "Title: Episode 12" in lines
    assert "From: A Podcast" in lines
    assert "Position: 1:00" in lines
    assert "Duration: 5:00" in lines
    assert "Remaining: 4:00" in lines
    assert "Progress: 20 percent" in lines
    assert "Speed: Normal" in lines


def test_a_live_stream_says_so_instead_of_guessing() -> None:
    lines = player_info_lines(_info(duration_ms=0, streaming=True))
    assert "Duration: not known for a live stream" in lines
    assert "Source: streaming" in lines
    assert not any(line.startswith("Remaining:") for line in lines)


def test_temporary_and_permanent_copies_are_distinguished() -> None:
    permanent = player_info_lines(_info(saved_permanently=True))
    temporary = player_info_lines(_info(saved_permanently=False))
    assert "Source: a file on this computer" in permanent
    assert "Source: a temporary copy on this computer" in temporary


def test_counts_appear_only_when_there_are_any() -> None:
    without = player_info_lines(_info())
    with_them = player_info_lines(_info(bookmark_count=3, note_count=1))
    assert not any(line.startswith("Bookmarks:") for line in without)
    assert "Bookmarks: 3" in with_them
    assert "Notes: 1" in with_them


def test_resume_position_is_reported_only_when_it_differs() -> None:
    same = player_info_lines(_info(resume_ms=60_000))
    different = player_info_lines(_info(resume_ms=200_000))
    assert not any(line.startswith("Will resume at:") for line in same)
    assert "Will resume at: 3:20" in different


def test_extras_are_appended() -> None:
    lines = player_info_lines(_info(extras=("Chapter 3 of 12",)))
    assert lines[-1] == "Chapter 3 of 12"


def test_text_is_the_lines_joined() -> None:
    info = _info()
    assert player_info_text(info) == "\n".join(player_info_lines(info))


def test_summary_is_one_spoken_sentence() -> None:
    assert player_info_summary(_info()) == ("Episode 12, 1 minute in, 4 minutes remaining.")


def test_summary_when_nothing_is_playing() -> None:
    assert player_info_summary(PlayerInfo()) == "Nothing is playing."


def test_summary_for_a_stream_omits_remaining() -> None:
    assert player_info_summary(_info(duration_ms=0)) == "Episode 12, 1 minute in."
