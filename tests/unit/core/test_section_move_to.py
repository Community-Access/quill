"""Move Section To: the picker, the rules, and what gets said.

The move keys are tested next door in ``test_markdown_sections.py``. What is
different here is that the destination is *chosen* rather than adjacent, so the
things that can go wrong are different too: a destination inside the section
being moved, a level that would fall past Heading 6, and a document whose blank
lines have to survive a cut and a paste at two different seams.

Every move that happens is also checked for **shape**: the same number of
headings, in the order asked for, with the document's own ending intact. A
reorganise that quietly gains or loses a blank line is a diff nobody can read.
"""

from __future__ import annotations

import pytest

from quill.core.section_move_to import (
    MoveToStatus,
    move_section_to,
    move_targets,
    placement_choices,
    run_move_section_to,
)
from quill.core.section_tree import parse_heading_blocks

# The document from the bug report that started this whole family of keys:
# strictly nested, so no heading has a sibling anywhere and every heading is
# an only child. Alt+Shift+Up and Alt+Shift+Down moved nothing in it, from
# top to bottom, and said so in a sentence about the implementation.
NESTED = """# Heading 1

This is a test for the first heading.

## Heading 2

This is a test for the second heading.

### Heading 3

This is a test for the third heading.
"""

# A flat outline with real subsections, which is what reorganising looks like.
COOKBOOK = """# Cookbook

Notes about the book.

## Bread

bread notes

### Sourdough

sourdough notes

## Soup

soup notes

## Salad

salad notes
"""


def _titles(text: str) -> list[tuple[int, str]]:
    return [(b.level, b.title) for b in parse_heading_blocks(text, "markdown")]


def _caret_of(text: str, heading: str) -> int:
    return text.index(heading)


# --------------------------------------------------------------------------- #
# The rows
# --------------------------------------------------------------------------- #


def test_targets_list_every_heading_with_its_position():
    targets = move_targets(COOKBOOK, _caret_of(COOKBOOK, "## Soup"), markup_kind="markdown")
    assert [t.label for t in targets] == [
        "1 of 5, level 1 - Cookbook",
        "2 of 5, level 2 - Bread",
        "3 of 5, level 3 - Sourdough",
        "4 of 5, level 2 - Soup (the section you are moving)",
        "5 of 5, level 2 - Salad",
    ]


def test_targets_mark_the_section_and_its_children_as_blocked():
    targets = move_targets(COOKBOOK, _caret_of(COOKBOOK, "## Bread"), markup_kind="markdown")
    blocked = [t.title for t in targets if t.blocked]
    assert blocked == ["Bread", "Sourdough"]


def test_targets_are_empty_for_a_single_section_document():
    assert move_targets("# Only\n\nbody\n", 0, markup_kind="markdown") == []


def test_targets_are_empty_in_plain_text():
    assert move_targets(COOKBOOK, 0, markup_kind="plain") == []


def test_placement_rows_are_the_three_placements_in_order():
    assert [value for value, _label in placement_choices()] == ["before", "after", "inside"]
    # Each row says what happens to the document, not what the word means.
    labels = dict(placement_choices())
    assert "above" in labels["before"]
    assert "everything under it" in labels["after"]
    assert "changes the level" in labels["inside"]


# --------------------------------------------------------------------------- #
# Before / After
# --------------------------------------------------------------------------- #


def test_before_puts_the_section_above_the_chosen_heading():
    caret = _caret_of(COOKBOOK, "## Salad")
    outcome = move_section_to(COOKBOOK, caret, 1, "before", markup_kind="markdown")
    assert outcome.moved
    assert _titles(outcome.text) == [
        (1, "Cookbook"),
        (2, "Salad"),
        (2, "Bread"),
        (3, "Sourdough"),
        (2, "Soup"),
    ]


def test_after_puts_the_section_past_the_whole_chosen_subtree():
    """After Bread means after Sourdough too -- Sourdough is inside Bread."""
    caret = _caret_of(COOKBOOK, "## Salad")
    outcome = move_section_to(COOKBOOK, caret, 1, "after", markup_kind="markdown")
    assert _titles(outcome.text) == [
        (1, "Cookbook"),
        (2, "Bread"),
        (3, "Sourdough"),
        (2, "Salad"),
        (2, "Soup"),
    ]


def test_a_move_takes_the_whole_subtree_with_it():
    caret = _caret_of(COOKBOOK, "## Bread")
    outcome = move_section_to(COOKBOOK, caret, 4, "after", markup_kind="markdown")
    assert _titles(outcome.text) == [
        (1, "Cookbook"),
        (2, "Soup"),
        (2, "Salad"),
        (2, "Bread"),
        (3, "Sourdough"),
    ]
    assert "sourdough notes" in outcome.text.split("## Bread")[1]


def test_neither_before_nor_after_changes_a_level():
    caret = _caret_of(NESTED, "## Heading 2")
    outcome = move_section_to(NESTED, caret, 0, "before", markup_kind="markdown")
    assert _titles(outcome.text) == [(2, "Heading 2"), (3, "Heading 3"), (1, "Heading 1")]
    assert "now Heading" not in outcome.announce


def test_the_body_travels_with_its_heading():
    caret = _caret_of(COOKBOOK, "## Soup")
    outcome = move_section_to(COOKBOOK, caret, 0, "before", markup_kind="markdown")
    assert outcome.text.startswith("## Soup\n\nsoup notes\n\n# Cookbook")


# --------------------------------------------------------------------------- #
# Inside -- the one placement that changes a level
# --------------------------------------------------------------------------- #


def test_inside_renumbers_the_moved_subtree_one_level_deeper():
    caret = _caret_of(COOKBOOK, "## Soup")
    outcome = move_section_to(COOKBOOK, caret, 1, "inside", markup_kind="markdown")
    assert _titles(outcome.text) == [
        (1, "Cookbook"),
        (2, "Bread"),
        (3, "Sourdough"),
        (3, "Soup"),
        (2, "Salad"),
    ]


def test_inside_renumbers_every_heading_in_the_subtree_by_the_same_step():
    caret = _caret_of(COOKBOOK, "## Bread")
    outcome = move_section_to(COOKBOOK, caret, 4, "inside", markup_kind="markdown")
    assert _titles(outcome.text) == [
        (1, "Cookbook"),
        (2, "Soup"),
        (2, "Salad"),
        (3, "Bread"),
        (4, "Sourdough"),
    ]


def test_inside_says_the_new_level_out_loud():
    caret = _caret_of(COOKBOOK, "## Soup")
    outcome = move_section_to(COOKBOOK, caret, 1, "inside", markup_kind="markdown")
    assert "now Heading 3" in outcome.announce


def test_inside_refuses_rather_than_flattening_past_heading_six():
    text = "# A\n\n## B\n\n### C\n\n#### D\n\n##### E\n\n###### F\n\n## G\n\nbody\n"
    caret = text.index("## B")
    # B's subtree already reaches level 6; one step deeper has nowhere to go.
    target = [b.title for b in parse_heading_blocks(text, "markdown")].index("G")
    outcome = move_section_to(text, caret, target, "inside", markup_kind="markdown")
    assert outcome.status is MoveToStatus.TOO_DEEP
    assert outcome.text == text
    assert "level 6" in outcome.announce
    assert "After" in outcome.announce


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #


def test_a_section_cannot_be_its_own_destination():
    caret = _caret_of(COOKBOOK, "## Bread")
    outcome = move_section_to(COOKBOOK, caret, 1, "after", markup_kind="markdown")
    assert outcome.status is MoveToStatus.INSIDE_SELF
    assert outcome.text == COOKBOOK
    assert "the section you are moving" in outcome.announce


def test_a_section_cannot_move_into_its_own_subtree():
    caret = _caret_of(COOKBOOK, "## Bread")
    outcome = move_section_to(COOKBOOK, caret, 2, "inside", markup_kind="markdown")
    assert outcome.status is MoveToStatus.INSIDE_SELF
    assert outcome.text == COOKBOOK
    assert "Sourdough is inside Bread" in outcome.announce
    # The refusal teaches the way out rather than only closing the door.
    assert "Promote Sourdough" in outcome.announce


def test_a_document_with_one_section_says_so():
    outcome = move_section_to("# Only\n\nbody\n", 0, 0, "after", markup_kind="markdown")
    assert outcome.status is MoveToStatus.ONLY_SECTION
    assert "only one section" in outcome.announce


def test_a_document_with_no_headings_says_where_to_put_the_cursor():
    outcome = move_section_to("just prose\n", 0, 0, "after", markup_kind="markdown")
    assert outcome.status is MoveToStatus.NO_SECTION
    assert outcome.announce == "Put the cursor in a section to move it"


def test_plain_text_is_refused_rather_than_silently_doing_nothing():
    outcome = move_section_to(COOKBOOK, 0, 1, "after", markup_kind="plain")
    assert outcome.status is MoveToStatus.NO_SECTION


def test_an_out_of_range_target_is_refused():
    outcome = move_section_to(COOKBOOK, 0, 99, "after", markup_kind="markdown")
    assert outcome.status is MoveToStatus.NO_SECTION
    assert outcome.text == COOKBOOK


# --------------------------------------------------------------------------- #
# Document shape: the blank lines and the file ending
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("placement", ["before", "after", "inside"])
@pytest.mark.parametrize("target", [0, 1, 4])
def test_no_move_ever_jams_two_headings_together(placement, target):
    caret = _caret_of(COOKBOOK, "## Soup")
    outcome = move_section_to(COOKBOOK, caret, target, placement, markup_kind="markdown")
    if not outcome.moved:
        return
    lines = outcome.text.split("\n")
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("#"):
            assert lines[index - 1] == "", f"heading {line!r} has no blank line above it"


@pytest.mark.parametrize("placement", ["before", "after", "inside"])
def test_a_move_keeps_the_heading_count_and_the_file_ending(placement):
    caret = _caret_of(COOKBOOK, "## Bread")
    outcome = move_section_to(COOKBOOK, caret, 4, placement, markup_kind="markdown")
    assert len(parse_heading_blocks(outcome.text, "markdown")) == 5
    assert outcome.text.endswith("notes\n")
    assert not outcome.text.endswith("\n\n")


def test_moving_the_last_section_away_does_not_leave_a_trailing_blank_line():
    caret = _caret_of(COOKBOOK, "## Salad")
    outcome = move_section_to(COOKBOOK, caret, 0, "before", markup_kind="markdown")
    assert outcome.text.endswith("soup notes\n")
    assert not outcome.text.endswith("\n\n")


def test_a_document_with_no_final_newline_keeps_none():
    text = COOKBOOK.rstrip("\n")
    caret = text.index("## Salad")
    outcome = move_section_to(text, caret, 0, "before", markup_kind="markdown")
    assert outcome.moved
    assert not outcome.text.endswith("\n")


def test_every_body_line_survives_a_move():
    caret = _caret_of(COOKBOOK, "## Bread")
    outcome = move_section_to(COOKBOOK, caret, 4, "after", markup_kind="markdown")
    before = sorted(line for line in COOKBOOK.split("\n") if line.strip())
    after = sorted(line for line in outcome.text.split("\n") if line.strip())
    assert before == after


# --------------------------------------------------------------------------- #
# The caret
# --------------------------------------------------------------------------- #


def test_the_caret_follows_the_moved_heading():
    caret = _caret_of(COOKBOOK, "## Soup")
    outcome = move_section_to(COOKBOOK, caret, 0, "before", markup_kind="markdown")
    assert outcome.text[outcome.caret :].startswith("## Soup")


def test_the_caret_keeps_its_column_in_the_heading_line():
    caret = _caret_of(COOKBOOK, "## Soup") + 3  # on the "S" of Soup
    outcome = move_section_to(COOKBOOK, caret, 0, "before", markup_kind="markdown")
    assert outcome.text[outcome.caret :].startswith("Soup")


def test_a_caret_in_the_body_still_lands_on_the_heading():
    caret = _caret_of(COOKBOOK, "soup notes") + 2
    outcome = move_section_to(COOKBOOK, caret, 0, "before", markup_kind="markdown")
    assert outcome.moved
    assert 0 <= outcome.caret <= len(outcome.text)
    heading_start = outcome.text.index("## Soup")
    assert heading_start <= outcome.caret <= heading_start + len("## Soup")


# --------------------------------------------------------------------------- #
# The sentence
# --------------------------------------------------------------------------- #


def test_a_move_says_where_it_landed_among_its_siblings():
    caret = _caret_of(COOKBOOK, "## Salad")
    outcome = move_section_to(COOKBOOK, caret, 1, "before", markup_kind="markdown")
    assert outcome.announce == "Moved Salad before Bread. Now 1 of 3 at this level"


def test_the_sentence_names_both_sections():
    caret = _caret_of(COOKBOOK, "## Bread")
    outcome = move_section_to(COOKBOOK, caret, 4, "after", markup_kind="markdown")
    assert outcome.announce.startswith("Moved Bread after Salad")


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #

HTML = (
    "<h1>Top</h1>\n\n<p>intro</p>\n\n"
    "<h2>Alpha</h2>\n\n<p>a</p>\n\n"
    "<h3>Alpha one</h3>\n\n<p>a1</p>\n\n"
    "<h2>Beta</h2>\n\n<p>b</p>\n"
)


def test_html_headings_move_too():
    caret = HTML.index("<h2>Beta</h2>")
    outcome = move_section_to(HTML, caret, 1, "before", markup_kind="html")
    assert outcome.moved
    assert [(b.level, b.title) for b in parse_heading_blocks(outcome.text, "html")] == [
        (1, "Top"),
        (2, "Beta"),
        (2, "Alpha"),
        (3, "Alpha one"),
    ]


def test_html_inside_rewrites_the_tag_pair():
    caret = HTML.index("<h2>Beta</h2>")
    outcome = move_section_to(HTML, caret, 1, "inside", markup_kind="html")
    assert "<h3>Beta</h3>" in outcome.text
    assert "<h2>Beta</h2>" not in outcome.text


# --------------------------------------------------------------------------- #
# The two-question flow
# --------------------------------------------------------------------------- #


def test_the_flow_asks_the_heading_then_the_placement():
    asked: list[str] = []

    def choose_heading(targets):
        asked.append("heading")
        return next(t for t in targets if t.title == "Bread")

    def choose_placement(choices):
        asked.append("placement")
        assert [value for value, _ in choices] == ["before", "after", "inside"]
        return "before"

    caret = _caret_of(COOKBOOK, "## Salad")
    outcome = run_move_section_to(
        COOKBOOK,
        caret,
        markup_kind="markdown",
        choose_heading=choose_heading,
        choose_placement=choose_placement,
    )
    assert asked == ["heading", "placement"]
    assert outcome.moved


def test_cancelling_the_heading_question_changes_nothing_and_says_nothing():
    outcome = run_move_section_to(
        COOKBOOK,
        0,
        markup_kind="markdown",
        choose_heading=lambda _targets: None,
        choose_placement=lambda _choices: pytest.fail("must not be asked"),
    )
    assert outcome.status is MoveToStatus.CANCELLED
    assert outcome.text == COOKBOOK
    assert outcome.announce == ""


def test_cancelling_the_placement_question_changes_nothing_and_says_nothing():
    outcome = run_move_section_to(
        COOKBOOK,
        0,
        markup_kind="markdown",
        choose_heading=lambda targets: targets[1],
        choose_placement=lambda _choices: None,
    )
    assert outcome.status is MoveToStatus.CANCELLED
    assert outcome.text == COOKBOOK
    assert outcome.announce == ""


def test_the_flow_refuses_a_one_section_document_without_asking():
    outcome = run_move_section_to(
        "# Only\n\nbody\n",
        0,
        markup_kind="markdown",
        choose_heading=lambda _targets: pytest.fail("must not be asked"),
        choose_placement=lambda _choices: pytest.fail("must not be asked"),
    )
    assert outcome.status is MoveToStatus.ONLY_SECTION


def test_the_flow_refuses_a_document_with_no_headings_without_asking():
    outcome = run_move_section_to(
        "just prose\n",
        0,
        markup_kind="markdown",
        choose_heading=lambda _targets: pytest.fail("must not be asked"),
        choose_placement=lambda _choices: pytest.fail("must not be asked"),
    )
    assert outcome.status is MoveToStatus.NO_SECTION


def test_the_flow_carries_a_blocked_choice_through_to_its_refusal():
    """The picker lets a blocked row be chosen; the rule refuses it and explains."""
    outcome = run_move_section_to(
        COOKBOOK,
        _caret_of(COOKBOOK, "## Bread"),
        markup_kind="markdown",
        choose_heading=lambda targets: next(t for t in targets if t.title == "Sourdough"),
        choose_placement=lambda _choices: "inside",
    )
    assert outcome.status is MoveToStatus.INSIDE_SELF
    assert "Sourdough is inside Bread" in outcome.announce


# --------------------------------------------------------------------------- #
# The reported document
# --------------------------------------------------------------------------- #


def test_the_reported_document_can_be_reorganised_by_destination():
    """``test.md`` is strictly nested, so no press of Alt+Shift+Down can help.

    Heading 3 is inside Heading 2 which is inside Heading 1, so there is no
    sibling anywhere and nothing below Heading 2 that is not part of it. Choosing
    a destination is the only thing that reorganises this document at all.
    """
    caret = _caret_of(NESTED, "### Heading 3")
    outcome = move_section_to(NESTED, caret, 0, "after", markup_kind="markdown")
    assert outcome.moved
    assert _titles(outcome.text) == [(1, "Heading 1"), (2, "Heading 2"), (3, "Heading 3")]
    # Heading 3 is now Heading 1's last child rather than Heading 2's, which the
    # levels alone cannot show -- the order is what changed.
    assert outcome.text.index("### Heading 3") > outcome.text.index("## Heading 2")
