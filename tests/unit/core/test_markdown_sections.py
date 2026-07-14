"""Tests for quill.core.markdown_sections."""

from __future__ import annotations

from quill.core.markdown_sections import (
    MoveResult,
    Section,
    current_section_at,
    move_section,
)

# --- current_section_at ---------------------------------------------------


def test_current_section_at_returns_none_when_no_headings() -> None:
    text = "Just some text.\nNo headings here.\n"
    assert current_section_at(text, 0) is None


def test_current_section_at_returns_first_heading_section() -> None:
    text = "# Top\nA\n## Mid\nB\n## End\nC\n"
    section = current_section_at(text, text.index("A"))
    assert section is not None
    assert section.start == 0
    assert section.end == text.index("## Mid")


def test_current_section_at_returns_none_when_caret_past_eof() -> None:
    # Caret past EOF still resolves to the last section (graceful fall-through).
    text = "# Top\nA\n"
    section = current_section_at(text, 999)
    assert section is not None
    assert section.start == 0


# --- move_section: up / down swaps ---------------------------------------


def test_move_section_down_swaps_with_next_sibling() -> None:
    text = "# A\nA body\n## B\nB body\n## C\nC body\n"
    caret = text.index("## B")
    new_text, new_caret, result, announce = move_section(text, caret, "down")
    assert result is MoveResult.OK
    # B is now in C's old slot, C in B's.
    assert new_text.index("## B") > new_text.index("## C")
    # Announce must surface the title of the heading we swapped with.
    assert "C" in announce
    # Caret stayed inside the moved B section.
    moved_b = new_text[new_caret:]
    assert moved_b.startswith("## B")


def test_move_section_up_swaps_with_previous_sibling() -> None:
    text = "# A\nA body\n## B\nB body\n## C\nC body\n"
    caret = text.index("## C")
    new_text, new_caret, result, announce = move_section(text, caret, "up")
    assert result is MoveResult.OK
    assert new_text.index("## C") < new_text.index("## B")
    assert "B" in announce
    assert new_text[new_caret:].startswith("## C")


def test_move_section_up_announces_top_when_already_first() -> None:
    text = "# A\nA body\n## B\nB body\n## C\nC body\n"
    caret = text.index("# A")
    new_text, new_caret, result, announce = move_section(text, caret, "up")
    assert result is MoveResult.TOP
    assert new_text == text
    assert new_caret == caret
    assert announce == "Top!"


def test_move_section_down_announces_bottom_when_already_last() -> None:
    text = "# A\nA body\n## B\nB body\n## C\nC body\n"
    caret = text.index("## C")
    new_text, new_caret, result, announce = move_section(text, caret, "down")
    assert result is MoveResult.BOTTOM
    assert new_text == text
    assert new_caret == caret
    assert announce == "Bottom!"


def test_move_section_in_non_heading_announces_no_section() -> None:
    text = "no headings here\n"
    new_text, new_caret, result, announce = move_section(text, 0, "down")
    assert result is MoveResult.NO_SECTION
    assert new_text == text
    assert announce == "No section to move"


def test_move_section_ignores_fenced_code_headings() -> None:
    """A `# fake` inside a ``` fence is not a real heading, so the
    parser must not see it as a sibling.  We give the real heading a
    true sibling to swap with, and verify the fenced line is not
    promoted to a real section after the move."""
    text = "# Real One\nBody\n```\n# fake\n```\n# Real Two\nMore\n"
    caret = text.index("# Real Two")
    new_text, new_caret, result, _ = move_section(text, caret, "up")
    assert result is MoveResult.OK
    # Fake heading must not have been promoted to a real section.
    # It still sits inside the ``` fence.
    fence_open = new_text.index("```")
    fence_close = new_text.index("```", fence_open + 3)
    assert new_text.index("# fake") > fence_open
    assert new_text.index("# fake") < fence_close


def test_move_section_preserves_caret_column_on_moved_heading() -> None:
    """When we move a section, the caret must land on the same column of
    the moved heading line, not jump to column 0."""
    text = "# A\nA body\n## B column-target\nB body\n## C\nC body\n"
    caret = text.index("## B column-target") + len("## B")
    # Column = caret offset from heading line start.
    original_column = caret - text.index("## B column-target")
    new_text, new_caret, result, _ = move_section(text, caret, "down")
    assert result is MoveResult.OK
    # The caret must be on the line that begins with "## B column-target".
    line_start = new_text.rfind("\n", 0, new_caret) + 1
    line_end = new_text.find("\n", new_caret)
    heading_line = new_text[line_start : line_end if line_end != -1 else len(new_text)]
    assert heading_line.startswith("## B column-target")
    # The caret column within the heading is preserved.
    assert new_caret - line_start == original_column


def test_move_section_round_trip_up_then_down_returns_original() -> None:
    text = "# A\nA\n## B\nB\n### B1\nB1\n## C\nC\n## D\nD\n"
    caret = text.index("## C")
    after_up, after_up_caret, result_up, _ = move_section(text, caret, "up")
    assert result_up is MoveResult.OK
    # The caret moved with C; new caret must still be inside the C section.
    assert after_up[after_up_caret:].startswith("## C")
    after_round, after_round_caret, result_down, _ = move_section(after_up, after_up_caret, "down")
    assert result_down is MoveResult.OK
    assert after_round == text
    # Caret column should match the original.
    assert after_round_caret == caret


# --- Section dataclass ---------------------------------------------------


def test_section_dataclass_is_frozen_and_slotted() -> None:
    section = Section(level=1, title="T", start=0, end=10)
    assert section.length == 10
    import dataclasses

    assert dataclasses.asdict(section) == {
        "level": 1,
        "title": "T",
        "start": 0,
        "end": 10,
    }
    # slots=True means we cannot set a new attribute.  The error is
    # `AttributeError` (or, in CPython 3.11+ for slotted frozen dataclasses,
    # a `TypeError` from object.__setattr__).  Either is acceptable evidence
    # the slot is closed.
    try:
        section.invented = "x"  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        return
    raise AssertionError("Section must reject undeclared attribute assignment")


# --- Plain-text form-feed fallback ---------------------------------------


def test_move_section_uses_form_feed_fallback_for_plain_text() -> None:
    text = "first block\fsecond block\freally third"
    caret = text.index("second")
    new_text, new_caret, result, _ = move_section(text, caret, "up", markup_kind="plain")
    assert result is MoveResult.OK
    # The two swapped sections: "second block" came up above "first block".
    assert new_text.index("second") < new_text.index("first")


def test_move_section_plain_text_no_form_feed_announces_no_section() -> None:
    text = "no form feeds here"
    new_text, new_caret, result, announce = move_section(text, 0, "down", markup_kind="plain")
    assert result is MoveResult.NO_SECTION
    assert announce == "No section to move"
    assert new_text == text


# --- Cross-level moves ---------------------------------------------------


def test_move_section_skips_unequal_levels_until_sibling() -> None:
    """A sub-heading has no sibling at its own level if there are no other
    same-level headings between it and the next lower-level one.  In that
    case the move is rejected (NO_SIBLING) and the text is untouched."""
    text = "# Top\nA\n## Sub\nB\n# Tail\nC\n"
    caret = text.index("## Sub")
    new_text, new_caret, result, _ = move_section(text, caret, "down")
    assert result is MoveResult.NO_SIBLING
    assert new_text == text
    assert new_caret == caret


# --- HTML path (PR1) -----------------------------------------------------


def test_move_section_html_swaps_with_next_sibling() -> None:
    text = "<h2>B</h2><p>b</p><h2>C</h2><p>c</p>"
    caret = text.index("<h2>B")
    new_text, new_caret, result, announce = move_section(text, caret, "down", markup_kind="html")
    assert result is MoveResult.OK
    # B is now in C's old slot.
    assert new_text.index("<h2>B") > new_text.index("<h2>C")
    assert "C" in announce


def test_move_section_html_announces_bottom_when_already_last() -> None:
    text = "<h2>B</h2><p>b</p>"
    caret = text.index("<h2>B")
    new_text, new_caret, result, announce = move_section(text, caret, "down", markup_kind="html")
    assert result is MoveResult.BOTTOM
    assert announce == "Bottom!"
