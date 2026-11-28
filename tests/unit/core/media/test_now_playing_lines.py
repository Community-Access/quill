"""The "Now playing" field's lines, shared by QUILL Cast and Quill Radio (plan Phase 2)."""

from __future__ import annotations

from quill.core.media.now_playing_lines import NowPlayingFacts, now_playing_lines, position_line


def test_a_file_shows_every_line_in_order() -> None:
    lines = now_playing_lines(
        NowPlayingFacts(
            title="Thursday",
            collection="The Daily",
            chapter_title="Listener mail",
            chapter_start_ms=754_000,
            chapter_index=2,
            chapter_count=12,
            position_ms=1_110_000,
            length_ms=3_480_000,
            speed=1.5,
            volume_percent=70,
            sleep="sleep in 20 minutes",
            published="2026-11-01",
            season=2,
            episode_number=14,
            where="file",
            chapter_source="Chapters from the publisher",
            transcript="transcript published",
        )
    )
    assert lines == [
        "Thursday, from The Daily",
        "Chapter: Listener mail, 12:34, 3 of 12",
        "Position: 18:30 of 58:00, 39:30 left, 31 percent",
        "Speed 1.5 times normal, volume 70 percent, sleep in 20 minutes",
        "Published 1 November 2026, season 2, episode 14, playing from the file",
        "Chapters from the publisher; transcript published",
    ]


def test_an_on_demand_stream_with_a_known_length() -> None:
    assert position_line(1_110_000, 3_480_000) == "18:30 of 58:00, 39:30 left, 31 percent"


def test_a_stream_whose_length_is_not_known_has_no_percentage() -> None:
    assert position_line(1_110_000, 0) == "18:30 in"


def test_a_live_stream_says_time_since_tuning_in() -> None:
    assert position_line(720_000, 0, live=True) == "Live, 12:00 since you tuned in"


def test_facts_nobody_knows_are_left_out() -> None:
    lines = now_playing_lines(NowPlayingFacts(title="Thursday", position_ms=30_000))
    assert lines == ["Thursday", "Position: 0:30 in"]


def test_an_untitled_chapter_is_untitled() -> None:
    facts = NowPlayingFacts(title="T", chapter_index=0, chapter_count=2)
    assert now_playing_lines(facts)[1] == "Chapter: Untitled, 0:00, 1 of 2"


def test_nothing_playing() -> None:
    assert now_playing_lines(NowPlayingFacts()) == ["Nothing is playing."]
