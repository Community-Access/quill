"""Ask AI about a video: the stretch, the frames and the transcript (roadmap A1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.demo_recording import DemoRecordingError
from quill.core.video_review import (
    Section,
    frame_times,
    frame_width,
    grid,
    parse_time,
    question_prompt,
    section,
    transcript_excerpt,
)

SRT = """1
00:00:01,000 --> 00:00:03,000
Hello and welcome.

2
00:01:10,500 --> 00:01:12,000
Now the settings.

3
00:02:30,000 --> 00:02:31,000
Goodbye.
"""


def test_times_parse_in_plain_forms():
    assert parse_time("75") == 75
    assert parse_time("1:05") == 65
    assert parse_time("1:02:03") == 3723
    assert parse_time("0:30.5") == 30.5
    with pytest.raises(DemoRecordingError):
        parse_time("soon")


def test_section_defaults_and_order():
    assert section(120.0) == Section(0.0, 120.0)
    assert section(120.0, "1:00", "") == Section(60.0, 120.0)
    assert section(120.0, "", "5:00").end == 120.0  # never past the end
    with pytest.raises(DemoRecordingError):
        section(120.0, "1:30", "1:00")


def test_frames_are_spread_across_the_stretch():
    assert frame_times(Section(0, 90), 3) == [15.0, 45.0, 75.0]
    assert frame_times(Section(0, 0), 3) == []
    assert grid(9) == (3, 3) and grid(6) == (3, 2) and grid(16) == (4, 4)


def test_transcript_excerpt_keeps_only_the_stretch():
    text = transcript_excerpt(SRT, Section(60, 120))
    assert text == "[1:10] Now the settings."
    assert transcript_excerpt(SRT, Section(0, 200)).count("[") == 3


def test_prompt_says_what_the_picture_is_and_asks_for_times():
    prompt = question_prompt(Path("Demo.mp4"), Section(60, 120), [70.0, 90.0], "[1:10] Now.")
    assert "contact sheet of 2 frames from the stretch from 1:00 to 2:00" in prompt
    assert "cite the frame times" in prompt and "Transcript of the same stretch" in prompt
    whole = question_prompt(Path("Demo.mp4"), Section(0, 60), [30.0], "")
    assert "the whole video" in whole and "Transcript" not in whole


def test_fewer_frames_are_drawn_bigger_and_no_sheet_outgrows_a_provider():
    # Shrinking a picture until a model takes it invents text (Kelly Ford's Quick Describe).
    assert frame_width(4) == 960 and frame_width(9) == 682 and frame_width(16) == 512
    for count in (4, 6, 9, 12, 16):
        assert grid(count)[0] * frame_width(count) <= 2048


def test_the_prompt_asks_for_honesty_about_small_text_and_gaps():
    prompt = question_prompt(Path("Demo.mp4"), Section(0, 60), [30.0], "")
    assert "say so instead of guessing" in prompt
    assert "between two frames" in prompt
