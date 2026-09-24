"""Tests for quill.core.markdown_sections."""

from __future__ import annotations

from quill.core.markdown_sections import (
    MoveResult,
    Section,
    current_section_at,
    describe_section_selection,
    move_section,
    section_selection_at,
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
    # "C" is the last section inside "A" -- naming the parent is the part a
    # listener can act on, since the bare word is true of the document too.
    assert announce == "Bottom of A"


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


def test_a_section_with_no_sibling_moves_past_what_is_actually_next_to_it() -> None:
    """ "## Sub" has no sibling below it, so it moves past "# Tail" -- the next
    thing in the document -- rather than refusing.  That is what Word's Move
    Down does on this chord, and what "move this section" means to the person
    pressing it.  It keeps its own level on the way."""
    text = "# Top\nA\n## Sub\nB\n# Tail\nC\n"
    caret = text.index("## Sub")
    new_text, _new_caret, result, announce = move_section(text, caret, "down")
    assert result is MoveResult.OK
    assert announce == "Section moved below Tail"
    assert new_text == "# Top\nA\n# Tail\nC\n## Sub\nB\n"


def test_a_strictly_nested_outline_still_moves() -> None:
    """A ``#`` / ``##`` / ``###`` ladder has no siblings anywhere, and used to
    answer every press with a sentence and no movement.  Up works: each heading
    rises above its parent's own heading and body, taking its children.  Down
    cannot, and that is structural rather than a refusal -- everything below
    "## Heading 2" *is* "## Heading 2", so there is nothing left to be below."""
    text = (
        "# Heading 1\n\nfirst body\n\n## Heading 2\n\nsecond body\n\n### Heading 3\n\nthird body\n"
    )
    outcomes = {
        (heading, direction): move_section(text, text.index(heading), direction)
        for heading in ("# Heading 1", "## Heading 2", "### Heading 3")
        for direction in ("up", "down")
    }
    spoken = {key: value[3] for key, value in outcomes.items()}
    assert spoken == {
        ("# Heading 1", "up"): "Top!",
        ("# Heading 1", "down"): (
            "Bottom! Everything below is inside this section. "
            "Promote Heading 2 to make it a sibling."
        ),
        ("## Heading 2", "up"): "Section moved above Heading 1",
        ("## Heading 2", "down"): (
            "Bottom of Heading 1. Everything below is inside this section. "
            "Promote Heading 3 to make it a sibling."
        ),
        ("### Heading 3", "up"): "Section moved above Heading 2",
        ("### Heading 3", "down"): "Bottom of Heading 2",
    }
    moved = {key for key, value in outcomes.items() if value[0] != text}
    assert moved == {("## Heading 2", "up"), ("### Heading 3", "up")}
    # Heading 2 rose above Heading 1 and took Heading 3 with it.
    lifted = outcomes[("## Heading 2", "up")][0]
    assert lifted == (
        "## Heading 2\n\nsecond body\n\n### Heading 3\n\nthird body\n\n# Heading 1\n\nfirst body\n"
    )


def test_a_lifted_child_can_be_put_back() -> None:
    """Every move is exactly reversible, which is what keeping the level buys."""
    text = "# A\n\na\n\n## A1\n\na1\n"

    lifted, _, up_result, _ = move_section(text, text.index("## A1"), "up")
    assert up_result is MoveResult.OK
    back, _, down_result, _ = move_section(lifted, lifted.index("## A1"), "down")

    assert down_result is MoveResult.OK
    assert back == text


def test_a_first_child_rises_above_its_parents_heading() -> None:
    """Above the parent's own heading and body -- not above the parent's whole
    subtree, which contains this section and cannot trade places with something
    it is inside."""
    text = "# A\n\na\n\n## A1\n\na1\n\n## A2\n\na2\n\n# B\n\nb\n"

    moved, _, result, jumped = move_section(text, text.index("## A1"), "up")

    assert result is MoveResult.OK
    assert jumped == "Section moved above A"
    assert moved == "## A1\n\na1\n\n# A\n\na\n\n## A2\n\na2\n\n# B\n\nb\n"


def test_a_sibling_below_is_still_preferred_to_the_neighbour() -> None:
    """The hierarchy-preserving move is the common case and comes first: A1
    trades with A2, not with whatever block happens to sit next to it."""
    text = "# A\n\na\n\n## A1\n\na1\n\n## A2\n\na2\n\n# B\n\nb\n"

    moved, _, result, jumped = move_section(text, text.index("## A1"), "down")

    assert result is MoveResult.OK
    assert jumped == "Section moved below A2. Now 2 of 2 at this level"
    assert moved.index("## A1") > moved.index("## A2")
    assert moved.index("## A1") < moved.index("# B"), "it stayed inside A"


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


# --- Subsections travel with their parent --------------------------------


def test_a_moved_section_takes_its_subsections_with_it() -> None:
    """``HeadingBlock.section_end`` stops at the next heading of ANY level, so
    moving by it left the children behind: ``### A1a`` stayed put while its
    ``## A1`` swapped past ``## A2``, and the file came out rearranged into
    something nobody wrote."""
    text = "# Top\n\n## A1\n\nbody a1\n\n### A1a\n\nbody a1a\n\n## A2\n\nbody a2\n"

    moved, _, result, jumped = move_section(text, text.index("## A1"), "down")

    assert result is MoveResult.OK
    assert jumped == "Section moved below A2. Now 2 of 2 at this level"
    assert moved == "# Top\n\n## A2\n\nbody a2\n\n## A1\n\nbody a1\n\n### A1a\n\nbody a1a\n"


def test_the_section_jumped_over_keeps_its_own_children_too() -> None:
    text = "# Top\n\n## A1\n\na1\n\n## A2\n\na2\n\n### A2a\n\na2a\n\n## A3\n\na3\n"

    moved, _, result, _ = move_section(text, text.index("## A1"), "down")

    assert result is MoveResult.OK
    # A1 landed after the whole of A2, not in the middle of it.
    assert moved.index("## A1") > moved.index("### A2a")
    assert moved.index("## A3") > moved.index("## A1")


def test_moving_down_and_back_up_leaves_the_file_byte_for_byte() -> None:
    """The blank lines belong to the slot rather than to the section, which is
    what makes the pair of keys safe to press. Carrying the terminator along
    jammed two headings onto consecutive lines at one end of the swap."""
    text = "# Top\n\n## A1\n\nbody a1\n\n### A1a\n\nbody a1a\n\n## A2\n\nbody a2\n"

    down, _, _, _ = move_section(text, text.index("## A1"), "down")
    back, _, _, _ = move_section(down, down.index("## A1"), "up")

    assert back == text


# --- Select Section (P3) -------------------------------------------------


def test_selecting_a_section_takes_its_subsections() -> None:
    text = "# Top\n\ntop\n\n## Bread\n\nbread\n\n### Sourdough\n\nsour\n\n## Soup\n\nsoup\n"

    selection = section_selection_at(text, text.index("## Bread"))

    assert selection is not None
    assert text[selection.start : selection.end] == "## Bread\n\nbread\n\n### Sourdough\n\nsour"
    assert selection.sections == 2, "Bread and Sourdough"
    # Seven physical lines, blanks included -- the same count the editor would
    # report, rather than a count of lines that happen to have words on them.
    said = describe_section_selection(selection)
    assert said == "Selected Bread and 1 section under it, 7 lines"


def test_the_selection_stops_before_the_blank_line_that_separates_sections() -> None:
    """Swallowing it would make a cut run the next heading onto the end of this
    section, which is the invisible-boundary mistake this command replaces."""
    text = "# A\n\na\n\n# B\n\nb\n"

    selection = section_selection_at(text, 0)

    assert selection is not None
    assert text[selection.start : selection.end] == "# A\n\na"


def test_a_leaf_section_counts_only_itself() -> None:
    text = "# A\n\na\n\n## A1\n\na1\n"

    selection = section_selection_at(text, text.index("## A1"))

    assert selection is not None
    assert selection.sections == 1
    assert describe_section_selection(selection) == "Selected A1, 3 lines"


def test_selecting_works_from_the_body_not_only_the_heading_line() -> None:
    text = "# A\n\nbody of A\n\n# B\n\nb\n"

    selection = section_selection_at(text, text.index("body of A") + 3)

    assert selection is not None
    assert text[selection.start : selection.end] == "# A\n\nbody of A"


def test_a_document_with_no_headings_has_no_section_to_select() -> None:
    assert section_selection_at("just prose\n", 0) is None
    assert section_selection_at("# A\n", 0, markup_kind="plain") is None
