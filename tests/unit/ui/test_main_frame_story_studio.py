from __future__ import annotations

from quill.ui.main_frame_story_studio import offset_to_line


def test_offset_at_start_is_line_one() -> None:
    assert offset_to_line("# Title\n\nBody\n", 0) == 1


def test_offset_counts_preceding_newlines() -> None:
    text = "# Part\n\n## Chapter\n\n### Scene\n"
    assert offset_to_line(text, text.index("## Chapter")) == 3
    assert offset_to_line(text, text.index("### Scene")) == 5


def test_negative_or_zero_offset_clamps_to_line_one() -> None:
    assert offset_to_line("abc", -5) == 1


def test_offset_past_end_clamps_to_last_line() -> None:
    assert offset_to_line("a\nb\nc", 999) == 3
