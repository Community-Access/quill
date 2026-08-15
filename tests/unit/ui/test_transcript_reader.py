"""The transcript reader: the timings are the point.

Transcripts have been fetchable and readable-as-a-document for a while; what was
missing was everything that needs to know *when* a line is spoken. These pin the
pure half of that -- the bridge between character offsets, which is what a text
control understands, and milliseconds, which is what a player understands -- plus
the writers that let Save As keep the timings instead of flattening them away.

No wx here on purpose: the mapping is where the bugs would be, and it is pure.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.transcripts import (
    TranscriptCue,
    cue_at,
    cues_to_srt,
    cues_to_text,
    cues_to_vtt,
    parse_transcript_cues,
)
from quill.ui.transcript_reader import (
    cue_index_for_offset,
    describe_position,
    line_starts,
)

_CUES = [
    TranscriptCue(0, 4_000, "Hello there"),
    TranscriptCue(4_000, 8_500, "Second line", speaker="Ann"),
    TranscriptCue(8_500, 12_000, "Third line"),
]


def test_line_starts_match_the_text_the_reader_shows() -> None:
    text = cues_to_text(_CUES)
    offsets = line_starts(_CUES)
    for cue, offset in zip(_CUES, offsets, strict=True):
        assert text[offset:].startswith(cue.spoken_label)


def test_a_blank_cue_occupies_no_line() -> None:
    # cues_to_text drops empty cues, so the offsets must not pretend they have
    # a line -- otherwise every offset after one is wrong and Enter seeks to
    # the wrong moment.
    cues = [_CUES[0], TranscriptCue(4_000, 4_500, "   "), _CUES[2]]
    text = cues_to_text(cues)
    offsets = line_starts(cues)
    assert text[offsets[2] :].startswith("Third line")


def test_the_caret_maps_back_to_the_cue_it_is_in() -> None:
    offsets = line_starts(_CUES)
    assert cue_index_for_offset(offsets, _CUES, 0) == 0
    assert cue_index_for_offset(offsets, _CUES, 5) == 0
    assert cue_index_for_offset(offsets, _CUES, offsets[1]) == 1
    assert cue_index_for_offset(offsets, _CUES, offsets[1] + 3) == 1
    assert cue_index_for_offset(offsets, _CUES, offsets[2]) == 2


def test_an_offset_past_the_end_still_lands_on_the_last_cue() -> None:
    # A caret at the very end of the control is an ordinary place to be, and
    # "no cue" there would make Enter refuse for no reason.
    offsets = line_starts(_CUES)
    assert cue_index_for_offset(offsets, _CUES, 10_000) == 2


def test_an_empty_transcript_maps_to_nothing_rather_than_crashing() -> None:
    assert line_starts([]) == []
    assert cue_index_for_offset([], [], 0) == -1


def test_positions_are_spoken_as_words_never_as_a_timecode() -> None:
    # "4:12" read aloud is an ambiguous pair of numbers unless you already know
    # it is a time. This is the rule the whole player stack follows.
    assert describe_position(TranscriptCue(252_000, 256_000, "x")) == "4 minutes 12 seconds"
    assert describe_position(TranscriptCue(0, 1, "x")) == "0 seconds"
    assert describe_position(TranscriptCue(3_661_000, 3_662_000, "x")) == "1 hour 1 minute 1 second"


def test_follow_playback_lands_on_the_line_being_spoken() -> None:
    assert cue_at(_CUES, 0) == 0
    assert cue_at(_CUES, 3_999) == 0
    assert cue_at(_CUES, 4_000) == 1
    # Between cues, the caret rests on the line just spoken rather than jumping
    # back to nothing.
    assert cue_at(_CUES, 12_500) == 2
    assert cue_at([], 500) == -1


@pytest.mark.parametrize(
    ("writer", "mime"),
    [(cues_to_vtt, "text/vtt"), (cues_to_srt, "application/x-subrip")],
)
def test_saving_keeps_the_timings_and_reads_back(writer, mime: str) -> None:
    # A writer that only looks right is worth nothing: the assertion is that the
    # file we hand somebody parses back into the cues we started with.
    round_tripped = parse_transcript_cues(writer(_CUES).encode("utf-8"), mime)
    assert [(c.start_ms, c.end_ms) for c in round_tripped] == [
        (c.start_ms, c.end_ms) for c in _CUES
    ]
    assert [c.text for c in round_tripped] == [c.spoken_label for c in _CUES]


def test_webvtt_is_written_with_its_header_and_srt_without_one() -> None:
    assert cues_to_vtt(_CUES).startswith("WEBVTT")
    assert cues_to_srt(_CUES).startswith("1\n")
    # SubRip uses a comma before the milliseconds; WebVTT uses a point.
    assert "00:00:04,000 --> 00:00:08,500" in cues_to_srt(_CUES)
    assert "00:00:04.000 --> 00:00:08.500" in cues_to_vtt(_CUES)


def test_writing_an_empty_transcript_is_not_an_error() -> None:
    assert cues_to_srt([]) == ""
    assert cues_to_vtt([]).strip() == "WEBVTT"
