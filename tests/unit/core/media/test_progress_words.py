"""The percentage through, in every player (Jeff, 2026-11-27)."""

from __future__ import annotations

from quill.core.media.progress_words import percent_phrase, percent_through, trusted_length_ms


def test_a_local_file_uses_the_engines_length() -> None:
    assert trusted_length_ms(3_480_000) == 3_480_000
    assert percent_phrase(1_110_000, 3_480_000) == "31 percent"


def test_an_on_demand_stream_with_a_length_from_mpv() -> None:
    assert trusted_length_ms(3_480_000, 3_500_000, buffering=True) == 3_480_000


def test_a_stream_whose_length_comes_only_from_the_feed() -> None:
    assert trusted_length_ms(0, 3_480_000) == 3_480_000
    # Still buffering and wildly off: the bytes so far are a guess.
    assert trusted_length_ms(600_000, 3_480_000, buffering=True) == 3_480_000
    # Fully local and different: the file is the truth.
    assert trusted_length_ms(600_000, 3_480_000) == 600_000


def test_a_live_stream_or_unknown_length_has_no_percentage() -> None:
    assert trusted_length_ms(0, 0) == 0
    assert percent_through(720_000, 0) is None
    assert percent_phrase(720_000, 0) == ""


def test_floored_so_it_never_says_100_before_the_end() -> None:
    assert percent_through(3_479_000, 3_480_000) == 99
    assert percent_through(3_480_000, 3_480_000) == 100
    assert percent_through(-5, 1_000) == 0


def test_the_sound_enhancements_offset_is_already_in_the_position() -> None:
    """Cast's controller adds the enhanced relay's offset in position_ms()
    (player_controller.py); the percentage is taken from that position."""
    offset, relay_position = 1_000_000, 110_000
    assert percent_phrase(offset + relay_position, 3_480_000) == "31 percent"
