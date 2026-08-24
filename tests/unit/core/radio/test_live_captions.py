"""Which caption is being spoken, and what the Captions window shows.

The pure half of the captions surface. Captions used to be drawn into the
picture by mpv -- pixels, which a screen reader cannot read and a braille
display cannot reach -- so this exists to make the readable version testable
without a window, a player, or a video.
"""

from __future__ import annotations

from quill.core.radio import live_captions


class _Cue:
    def __init__(self, start_ms: int, text: str) -> None:
        self.start_ms = start_ms
        self.end_ms = start_ms + 1500
        self.text = text


CUES = [
    _Cue(0, "Good evening."),
    _Cue(2000, "Tonight, the weather."),
    _Cue(5000, "And then, the news."),
]


def test_before_the_first_line_nothing_is_current() -> None:
    # A window that showed line one before it was spoken would be lying about
    # where playback is.
    assert live_captions.cue_index_at(CUES, 0) == 0
    assert live_captions.cue_index_at(CUES, -50) == 0
    assert live_captions.cue_index_at([], 1000) == -1


def test_the_current_line_is_the_last_one_started() -> None:
    assert live_captions.cue_index_at(CUES, 1999) == 0
    assert live_captions.cue_index_at(CUES, 2000) == 1
    assert live_captions.cue_index_at(CUES, 4999) == 1
    assert live_captions.cue_index_at(CUES, 60_000) == 2


def test_silence_between_lines_holds_the_last_thing_said() -> None:
    """Not blank. A window that empties between sentences reads as broken."""
    gap = [_Cue(0, "One."), _Cue(30_000, "Two.")]
    assert live_captions.cue_index_at(gap, 10_000) == 0


def test_the_window_keeps_what_has_already_been_said() -> None:
    """A single flashing line is only usable if you read at its speed."""
    text = live_captions.visible_text(CUES, 2)
    assert text.splitlines() == [
        "Good evening.",
        "Tonight, the weather.",
        "> And then, the news.",
    ]


def test_the_current_line_is_marked_by_a_character_not_a_colour() -> None:
    # Colour is unavailable to a screen reader and unreliable for a
    # colour-blind reader; the marker has to be part of the text.
    assert live_captions.visible_text(CUES, 0) == "> Good evening."


def test_the_kept_history_is_bounded() -> None:
    many = [_Cue(i * 1000, f"Line {i}") for i in range(200)]
    lines = live_captions.visible_text(many, 199, context=5).splitlines()
    assert len(lines) == 6
    assert lines[-1] == "> Line 199"


def test_nothing_is_shown_before_playback_reaches_the_captions() -> None:
    assert live_captions.visible_text(CUES, -1) == ""
    assert live_captions.current_text(CUES, -1) == ""


def test_the_current_line_can_be_had_on_its_own_unmarked() -> None:
    assert live_captions.current_text(CUES, 1) == "Tonight, the weather."
    assert live_captions.current_text(CUES, 99) == ""


def test_an_empty_line_is_skipped_rather_than_shown_as_a_blank() -> None:
    cues = [_Cue(0, "One."), _Cue(1000, "   "), _Cue(2000, "Three.")]
    assert live_captions.visible_text(cues, 2).splitlines() == ["One.", "> Three."]
