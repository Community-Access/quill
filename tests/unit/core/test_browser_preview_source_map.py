"""Source-mapped preview rendering (#1257).

The live side preview stamps each block-level Markdown element with a
``data-src="<line>"`` attribute so a right-clicked (or Entered) block maps back
to a caret offset in the editor. Everything else — export, clipboard, publish —
must keep emitting clean markup with no editor-only attributes.
"""

from __future__ import annotations

import re

from quill.core.browser_preview import (
    markup_offset_for_line,
    render_preview_body,
)


def test_source_map_off_by_default_emits_no_data_src() -> None:
    body = render_preview_body("# Title\n\nHello\n\n- one\n- two", "markdown")
    assert "data-src" not in body


def test_source_map_stamps_heading_line() -> None:
    body = render_preview_body("# Title\n\nHello", "markdown", source_map=True)
    assert '<h1 id="title" data-src="0">' in body


def test_source_map_stamps_paragraph_start_line() -> None:
    # Line 0 blank, heading on 1, blank 2, paragraph starts on line 3.
    text = "\n# H\n\nBody paragraph"
    body = render_preview_body(text, "markdown", source_map=True)
    assert '<h1 id="h" data-src="1">' in body
    assert '<p data-src="3">' in body


def test_source_map_stamps_each_list_item() -> None:
    body = render_preview_body("- alpha\n- beta\n- gamma", "markdown", source_map=True)
    assert '<li data-src="0">' in body
    assert '<li data-src="1">' in body
    assert '<li data-src="2">' in body


def test_source_map_stamps_blockquote_table_code_and_hr() -> None:
    text = "> quote\n\n---\n\n| a | b |\n| - | - |\n| 1 | 2 |\n\n```\ncode\n```"
    body = render_preview_body(text, "markdown", source_map=True)
    assert '<blockquote data-src="0">' in body
    assert '<hr data-src="2">' in body
    assert '<table data-src="4">' in body
    # Fenced code block opens on line 8 (0-based).
    assert re.search(r'<pre data-src="8"><code>', body)


def test_markup_offset_for_line_basic() -> None:
    text = "# Title\n\nHello world\nsecond line"
    assert markup_offset_for_line(text, 0) == 0
    assert markup_offset_for_line(text, 1) == len("# Title\n")
    assert markup_offset_for_line(text, 2) == len("# Title\n\n")
    assert markup_offset_for_line(text, 3) == len("# Title\n\nHello world\n")


def test_markup_offset_for_line_handles_crlf() -> None:
    text = "line0\r\nline1\r\nline2"
    assert markup_offset_for_line(text, 0) == 0
    assert markup_offset_for_line(text, 1) == len("line0\r\n")
    assert markup_offset_for_line(text, 2) == len("line0\r\nline1\r\n")


def test_markup_offset_for_line_clamps_out_of_range() -> None:
    text = "a\nb\nc"
    assert markup_offset_for_line(text, -5) == 0
    assert markup_offset_for_line(text, 999) == len(text)


def test_offset_round_trips_to_the_rendered_block() -> None:
    # The offset a stamped line maps to must land at the start of that block's
    # source text, so the editor caret lands where the preview element began.
    text = "# One\n\nA paragraph.\n\n## Two\n\nMore text."
    body = render_preview_body(text, "markdown", source_map=True)
    match = re.search(r'<h2 id="two" data-src="(\d+)">', body)
    assert match is not None
    line = int(match.group(1))
    offset = markup_offset_for_line(text, line)
    assert text[offset:].startswith("## Two")
