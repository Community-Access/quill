"""The cue when the caret arrives on a line with an inline note (wx-free)."""

from __future__ import annotations

from quill.core.inline_note_cue import (
    NOTE_LINE_CUE_CHOICES,
    NoteLineCue,
    coerce_note_line_cue,
    cue_channels,
    noted_spans,
)

TEXT = "one\ntwo noted\nthree\nfour noted\nfive noted\n"


def _cue_for(*ranges: tuple[int, int]) -> NoteLineCue:
    cue = NoteLineCue()
    cue.use(noted_spans(TEXT, ranges))
    return cue


def test_arriving_cues_and_moving_along_the_line_does_not() -> None:
    start = TEXT.index("two")
    cue = _cue_for((start, start + 3))
    assert cue.arrive(0) is False  # line one: nothing here
    assert cue.arrive(start) is True  # arrived on the noted line
    assert cue.arrive(start + 4) is False  # Right arrow along it
    assert cue.arrive(start + len("two noted")) is False  # End
    assert cue.arrive(TEXT.index("three")) is False  # left it
    assert cue.arrive(start + 2) is True  # and back again


def test_neighbouring_noted_lines_each_cue() -> None:
    four, five = TEXT.index("four"), TEXT.index("five")
    cue = _cue_for((four, four + 4), (five, five + 4))
    assert cue.arrive(four) is True
    assert cue.arrive(five) is True


def test_a_note_across_several_lines_is_one_place() -> None:
    four, five = TEXT.index("four"), TEXT.index("five")
    cue = _cue_for((four + 2, five + 2))
    assert cue.arrive(four) is True
    assert cue.arrive(five) is False


def test_settle_moves_without_a_cue_and_forget_starts_over() -> None:
    start = TEXT.index("two")
    cue = _cue_for((start, start + 3))
    cue.settle(start)
    assert cue.arrive(start + 1) is False
    cue.forget()
    assert cue.arrive(start + 1) is True


def test_sound_speech_and_off() -> None:
    assert cue_channels("sound", has_sound=True) == (True, False, True)
    # No clip in the pack: the word instead, never silence (action_feedback).
    assert cue_channels("sound", has_sound=False) == (False, True, False)
    assert cue_channels("speech", has_sound=True) == (False, True, False)
    assert cue_channels("off", has_sound=True) == (False, False, False)


def test_a_stored_value_out_of_range_is_the_default() -> None:
    assert NOTE_LINE_CUE_CHOICES[0] == "sound"
    assert coerce_note_line_cue("SPEECH ") == "speech"
    assert coerce_note_line_cue("loud") == "sound"
    assert coerce_note_line_cue(None) == "sound"
