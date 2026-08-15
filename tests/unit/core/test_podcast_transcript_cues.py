"""Tests for timed transcript cues -- the piece both Cast and Radio lacked.

Pure: no network, no files. The WebVTT fixture carries the inline markup real
files carry (speaker voice tags, per-word timestamps, italics) because that is
what breaks a naive parser.
"""

from __future__ import annotations

import json

import pytest

from quill.core.podcasts.transcripts import (
    TranscriptCue,
    TranscriptError,
    cue_at,
    cues_to_text,
    parse_transcript,
    parse_transcript_cues,
)

_VTT = b"""WEBVTT

NOTE this is a comment block and is not spoken

1
00:00:00.540 --> 00:00:04.200
Podcasting 2.0 for July.

2
00:00:04.200 --> 00:00:08.000
<v Adam>Hello <i>everybody</i>, and <00:00:05.100>welcome.
"""

_SRT = b"""1
00:00:01,000 --> 00:00:03,500
First line.

2
00:00:03,500 --> 00:00:06,000
Second line.
"""

_VTT_NO_HOURS = b"""WEBVTT

00:04.000 --> 00:08.000
Short form timestamps.
"""

_PODCAST_JSON = json.dumps({
    "version": "1.0.0",
    "segments": [
        {"speaker": "Alice", "startTime": 0.5, "endTime": 2.25, "body": "Hello there."},
        {"speaker": "Bob", "startTime": 2.25, "endTime": 4.0, "body": "General Kenobi."},
        {"speaker": "Bob", "startTime": 4.0, "endTime": 5.0, "body": "   "},
    ],
}).encode()

_JSON3 = json.dumps({
    "events": [
        {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "Captured "}, {"utf8": "free."}]},
        {"tStartMs": 3000, "dDurationMs": 1500, "segs": [{"utf8": "Second cue."}]},
        {"tStartMs": 5000, "dDurationMs": 500, "segs": [{"utf8": "\n"}]},
    ]
}).encode()


def test_webvtt_becomes_timed_cues_with_markup_stripped() -> None:
    cues = parse_transcript_cues(_VTT, "text/vtt")
    assert len(cues) == 2
    assert cues[0].start_ms == 540 and cues[0].end_ms == 4200
    assert cues[0].text == "Podcasting 2.0 for July."
    # <v Adam>, <i>, and the per-word <00:00:05.100> timestamp are all gone.
    assert cues[1].text == "Hello everybody, and welcome."
    assert cues[1].start_ms == 4200


def test_srt_uses_the_same_parser_and_comma_decimals() -> None:
    cues = parse_transcript_cues(_SRT, "application/srt")
    assert [c.text for c in cues] == ["First line.", "Second line."]
    assert cues[0].start_ms == 1000 and cues[1].end_ms == 6000


def test_webvtt_without_an_hours_field_still_parses() -> None:
    cues = parse_transcript_cues(_VTT_NO_HOURS, "text/vtt")
    assert cues[0].start_ms == 4000 and cues[0].end_ms == 8000


def test_podcasting_2_json_carries_speakers() -> None:
    cues = parse_transcript_cues(_PODCAST_JSON, "application/json")
    assert [c.speaker for c in cues] == ["Alice", "Bob"]  # the blank body is dropped
    assert cues[0].start_ms == 500 and cues[0].end_ms == 2250
    assert cues[0].spoken_label == "Alice: Hello there."


def test_youtube_json3_captions_parse() -> None:
    # The format that arrives free with every YouTube resolve and was discarded.
    cues = parse_transcript_cues(_JSON3, "application/json")
    assert [c.text for c in cues] == ["Captured free.", "Second cue."]
    assert cues[0].start_ms == 1000 and cues[0].end_ms == 3000


def test_invalid_json_raises_but_unrecognised_text_does_not() -> None:
    with pytest.raises(TranscriptError):
        parse_transcript_cues(b"{not json", "application/json")
    assert parse_transcript_cues(b"just some prose with no timings", "text/plain") == []
    assert parse_transcript_cues(b"", "text/vtt") == []


def test_cues_to_text_matches_the_existing_plain_text_parser() -> None:
    # The contract that keeps one parser instead of two that drift: the text
    # form is the cue form with the timings dropped.
    cues = parse_transcript_cues(_SRT, "application/srt")
    assert cues_to_text(cues) == parse_transcript(_SRT, "application/srt")


def test_parse_transcript_is_unchanged_by_the_cue_work() -> None:
    # The existing Cast behaviour is the regression gate.
    assert parse_transcript(_SRT, "application/srt") == "First line.\nSecond line."
    assert parse_transcript(b"plain text", "text/plain") == "plain text"


def test_cue_at_finds_the_line_being_spoken() -> None:
    cues = [
        TranscriptCue(0, 1000, "a"),
        TranscriptCue(1000, 2000, "b"),
        TranscriptCue(2000, 3000, "c"),
    ]
    assert cue_at(cues, 0) == 0
    assert cue_at(cues, 999) == 0
    assert cue_at(cues, 1000) == 1
    assert cue_at(cues, 2500) == 2


def test_cue_at_rests_on_the_last_spoken_line_during_a_gap() -> None:
    # A reader's caret must not jump back to nothing between cues.
    cues = [TranscriptCue(0, 1000, "a"), TranscriptCue(5000, 6000, "b")]
    assert cue_at(cues, 3000) == 0
    assert cue_at(cues, 99_000) == 1


def test_cue_at_before_the_first_cue_and_on_an_empty_transcript() -> None:
    assert cue_at([TranscriptCue(500, 1000, "a")], 0) == -1
    assert cue_at([], 1234) == -1


def test_cue_at_is_a_binary_search_not_a_scan() -> None:
    # Follow Playback calls this on every position update; a transcript can run
    # to thousands of cues, so this must not be linear.
    cues = [TranscriptCue(i * 1000, i * 1000 + 900, f"line {i}") for i in range(50_000)]
    assert cue_at(cues, 49_999_000) == 49_999
    assert cue_at(cues, 25_000_500) == 25_000
