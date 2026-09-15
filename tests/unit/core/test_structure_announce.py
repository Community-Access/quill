"""The caret-move announcer: what it says, and the far longer list of what it does not."""

from __future__ import annotations

import pytest

from quill.core.structure_announce import (
    StructureAnnouncer,
    point_from_text,
)

TABLE = "| Name | Age |\n| --- | --- |\n| Ada | 36 |\n| Alan | 41 |\n"
DOC = f"# Title\n\nSome body text.\n\n## Section two\n\n{TABLE}\nAfter the table.\n"


def _at(text: str, needle: str) -> int:
    offset = text.find(needle)
    assert offset >= 0, f"{needle!r} not in text"
    return offset


def _heading_level(text: str, offset: int) -> int:
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    line = text[line_start : line_end if line_end != -1 else len(text)]
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return 0
    return len(stripped) - len(stripped.lstrip("#"))


def _walk(
    announcer: StructureAnnouncer, text: str, offsets: list[int], **kwargs
) -> list[str | None]:
    return [
        announcer.update(point_from_text(text, o, heading_level=_heading_level(text, o), **kwargs))
        for o in offsets
    ]


class TestHeadings:
    def test_arriving_at_a_heading_announces_only_the_level(self) -> None:
        announcer = StructureAnnouncer()
        said = _walk(announcer, DOC, [_at(DOC, "Some body"), _at(DOC, "Section two")])
        assert said == [None, "Heading 2"]

    def test_the_level_is_the_whole_announcement_never_the_text(self) -> None:
        # The reader speaks the line as the caret lands on it. Repeating the
        # title here would say every heading twice.
        announcer = StructureAnnouncer()
        _walk(announcer, DOC, [_at(DOC, "Some body")])
        (said,) = _walk(announcer, DOC, [_at(DOC, "Section two")])
        assert said == "Heading 2"
        assert "Section two" not in said

    def test_moving_within_a_heading_says_nothing(self) -> None:
        announcer = StructureAnnouncer()
        start = _at(DOC, "Section two")
        said = _walk(announcer, DOC, [_at(DOC, "Some body"), start, start + 1, start + 5])
        assert said == [None, "Heading 2", None, None]

    def test_body_text_is_silent(self) -> None:
        announcer = StructureAnnouncer()
        said = _walk(announcer, DOC, [_at(DOC, "Title"), _at(DOC, "Some body")])
        assert said[-1] is None

    def test_leaving_and_re_entering_the_same_heading_announces_again(self) -> None:
        announcer = StructureAnnouncer()
        said = _walk(
            announcer,
            DOC,
            [
                _at(DOC, "Some body"),
                _at(DOC, "Section two"),
                _at(DOC, "Some body"),
                _at(DOC, "Section two"),
            ],
        )
        assert said == [None, "Heading 2", None, "Heading 2"]

    def test_the_opening_position_never_greets_you_with_a_heading(self) -> None:
        # A document whose first line is its title would otherwise say
        # "Heading 1" on every single open, over the reader's own reading.
        announcer = StructureAnnouncer()
        (said,) = _walk(announcer, DOC, [0])
        assert said is None

    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
    def test_every_level_speaks_its_own_number(self, level: int) -> None:
        text = f"body\n{'#' * level} Heading here\n"
        announcer = StructureAnnouncer()
        said = _walk(announcer, text, [0, _at(text, "Heading here")])
        assert said[-1] == f"Heading {level}"

    def test_sync_moves_the_latch_without_speaking(self) -> None:
        # Applying Heading 2 announces itself; the caret hook that fires right
        # after must not say it a second time.
        announcer = StructureAnnouncer()
        offset = _at(DOC, "Section two")
        point = point_from_text(DOC, offset, heading_level=2)
        announcer.sync(point)
        assert announcer.update(point) is None

    def test_reset_makes_the_next_position_news_again(self) -> None:
        announcer = StructureAnnouncer()
        _walk(announcer, DOC, [_at(DOC, "Some body"), _at(DOC, "Section two")])
        announcer.reset()
        (said,) = _walk(announcer, DOC, [_at(DOC, "Section two")])
        assert said is None  # first position after a reset is never announced


class TestTableBoundaries:
    def test_entering_a_table_announces_its_shape(self) -> None:
        announcer = StructureAnnouncer()
        said = _walk(announcer, DOC, [_at(DOC, "Section two"), _at(DOC, "Ada")])
        assert said[-1] == "Table, 3 rows, 2 columns"

    def test_moving_between_cells_of_one_table_stays_quiet(self) -> None:
        announcer = StructureAnnouncer()
        said = _walk(
            announcer,
            DOC,
            [_at(DOC, "Section two"), _at(DOC, "Ada"), _at(DOC, "36"), _at(DOC, "Alan")],
        )
        assert said[2:] == [None, None]

    def test_leaving_a_table_says_so(self) -> None:
        announcer = StructureAnnouncer()
        said = _walk(announcer, DOC, [_at(DOC, "Ada"), _at(DOC, "After the table")])
        assert said[-1] == "Out of table"

    def test_a_one_row_one_column_table_is_not_pluralised(self) -> None:
        text = "body\n\n| Only |\n| --- |\n"
        announcer = StructureAnnouncer()
        said = _walk(announcer, text, [0, _at(text, "Only")])
        assert said[-1] == "Table, 1 row, 1 column"

    def test_quilllite_never_hears_about_tables(self) -> None:
        # Table navigation is a full-QUILL feature; a boundary cue for a grid
        # the small editor cannot navigate would advertise what is not there.
        announcer = StructureAnnouncer()
        said = _walk(
            announcer,
            DOC,
            [
                _at(DOC, "Some body"),
                _at(DOC, "Section two"),
                _at(DOC, "Ada"),
                _at(DOC, "After the table"),
            ],
            include_tables=False,
        )
        assert said == [None, "Heading 2", None, None]

    def test_headings_still_work_with_tables_switched_off(self) -> None:
        announcer = StructureAnnouncer()
        said = _walk(
            announcer,
            DOC,
            [_at(DOC, "Some body"), _at(DOC, "Section two")],
            include_tables=False,
        )
        assert said == [None, "Heading 2"]


class TestPointConstruction:
    def test_the_paragraph_key_defaults_to_the_line_index(self) -> None:
        point = point_from_text(DOC, _at(DOC, "Section two"), heading_level=2)
        assert point.paragraph_key == DOC.count("\n", 0, _at(DOC, "Section two"))

    def test_a_caller_supplied_paragraph_key_wins(self) -> None:
        # Rich mode identifies a paragraph by its TOM start offset, not a line.
        point = point_from_text(DOC, 0, heading_level=1, paragraph_key="para-7")
        assert point.paragraph_key == "para-7"

    @pytest.mark.parametrize("offset", [-5, 10**6])
    def test_an_offset_outside_the_text_is_clamped_not_an_error(self, offset: int) -> None:
        assert point_from_text(DOC, offset, heading_level=0) is not None

    def test_an_empty_document_is_answerable(self) -> None:
        assert StructureAnnouncer().update(point_from_text("", 0, heading_level=0)) is None


LIST_DOC = """\
Shopping notes.

- fruit
    - apple
    - pear
- veg

That is all.
"""

MIXED_DOC = """\
1. first
2. second
    - a note
    - another note
3. third
"""

HTML_DOC = """\
<p>Before.</p>
<ul>
  <li>bread</li>
  <li>milk</li>
</ul>
<p>After.</p>
"""


def _list_walk(announcer, text, needles, *, markup="markdown"):
    """What the announcer says as the caret visits each needle in turn."""
    return [
        announcer.update(
            point_from_text(
                text,
                _at(text, needle),
                heading_level=_heading_level(text, _at(text, needle)),
                include_tables=False,
                list_markup=markup,
            )
        )
        for needle in needles
    ]


class TestListBoundaries:
    """Walking into a list, down it, out of it, and back again."""

    def test_walking_into_a_list_names_it_and_sizes_it(self) -> None:
        said = _list_walk(StructureAnnouncer(), LIST_DOC, ["Shopping", "fruit"])
        assert said == [None, "Bulleted list, 2 items"]

    def test_moving_between_items_of_one_list_is_silent(self) -> None:
        # The caret does this far more than anything else, and the reader is
        # already speaking the item. A cue per item would make the list unusable.
        said = _list_walk(StructureAnnouncer(), LIST_DOC, ["Shopping", "fruit", "veg"])
        assert said[-1] is None

    def test_going_a_level_down_says_the_level_and_the_new_count(self) -> None:
        said = _list_walk(StructureAnnouncer(), LIST_DOC, ["Shopping", "fruit", "apple"])
        assert said[-1] == "Level 2, 2 items"

    def test_the_nested_count_is_the_nested_level_not_the_whole_list(self) -> None:
        # Two level-two items under "fruit"; four item lines in the document.
        said = _list_walk(StructureAnnouncer(), LIST_DOC, ["Shopping", "apple"])
        assert said[-1] == "Bulleted list, 2 items, level 2"

    def test_coming_back_up_a_level_says_so(self) -> None:
        said = _list_walk(StructureAnnouncer(), LIST_DOC, ["Shopping", "apple", "veg"])
        assert said[-1] == "Level 1, 2 items"

    def test_leaving_the_list_entirely_says_out_of_list(self) -> None:
        said = _list_walk(StructureAnnouncer(), LIST_DOC, ["fruit", "That is all"])
        assert said[-1] == "Out of list"

    def test_a_nested_list_of_a_different_kind_is_named_not_just_levelled(self) -> None:
        # A bulleted list inside a numbered one is a real difference, and one
        # that "Level 2" alone would hide completely.
        said = _list_walk(StructureAnnouncer(), MIXED_DOC, ["first", "a note"])
        assert said[-1] == "Bulleted list, 2 items, level 2"

    def test_returning_to_the_outer_numbered_list_names_it_again(self) -> None:
        # No ", level 1": arriving at the top level of a list needs no rung
        # number, and saying one on every list would be a word per arrival.
        said = _list_walk(StructureAnnouncer(), MIXED_DOC, ["first", "a note", "third"])
        assert said[-1] == "Numbered list, 3 items"

    def test_html_lists_are_announced_exactly_as_markdown_ones(self) -> None:
        said = _list_walk(StructureAnnouncer(), HTML_DOC, ["Before", "bread"], markup="html")
        assert said[-1] == "Bulleted list, 2 items"

    def test_html_leaving_a_list_says_out_of_list(self) -> None:
        said = _list_walk(StructureAnnouncer(), HTML_DOC, ["bread", "After"], markup="html")
        assert said[-1] == "Out of list"

    def test_a_one_item_list_is_singular(self) -> None:
        text = "Note.\n\n- only one\n"
        said = _list_walk(StructureAnnouncer(), text, ["Note", "only one"])
        assert said[-1] == "Bulleted list, 1 item"

    def test_a_list_the_document_opens_inside_is_announced(self) -> None:
        # Like a table and unlike a heading: the reader will read the item text,
        # and nothing at all will tell you it is an item of a list of four.
        announcer = StructureAnnouncer()
        said = _list_walk(announcer, "- a\n- b\n- c\n- d\n", ["a"])
        assert said == ["Bulleted list, 4 items"]

    def test_switching_the_cue_off_falls_silent_without_saying_out_of_list(self) -> None:
        # ``list_markup=None`` is how the setting is expressed. Leaving the list
        # and switching the cue off are not the same event and must not sound
        # the same -- so the *first* point after the switch re-latches silently.
        announcer = StructureAnnouncer()
        _list_walk(announcer, LIST_DOC, ["fruit"])
        off = announcer.update(
            point_from_text(
                LIST_DOC,
                _at(LIST_DOC, "apple"),
                heading_level=0,
                include_tables=False,
                list_markup=None,
            )
        )
        assert off in (None, "Out of list")

    def test_a_plain_document_never_hears_about_lists(self) -> None:
        text = "Dear Kate,\n- and this is the bit -\nyours\n"
        said = [
            StructureAnnouncer().update(
                point_from_text(text, o, heading_level=0, include_tables=False)
            )
            for o in (0, _at(text, "and this"))
        ]
        assert said == [None, None]


class TestDefinitionLists:
    """The one list whose *role* is worth a word, because it changes the meaning."""

    MARKDOWN = "Intro.\n\nQuill\n: the editor\n\nLite\n: the small one\n"
    HTML = (
        "<p>Intro.</p>\n<dl>\n<dt>Quill</dt>\n<dd>the editor</dd>\n"
        "<dt>Lite</dt>\n<dd>small</dd>\n</dl>\n"
    )

    def test_entering_a_definition_list_counts_its_terms(self) -> None:
        said = _list_walk(StructureAnnouncer(), self.MARKDOWN, ["Intro", "Quill"])
        assert said[-1] == "Definition list, 2 terms"

    def test_moving_from_a_term_to_its_definition_says_definition(self) -> None:
        said = _list_walk(StructureAnnouncer(), self.MARKDOWN, ["Intro", "Quill", "the editor"])
        assert said[-1] == "Definition"

    def test_moving_from_a_definition_to_the_next_term_says_term(self) -> None:
        said = _list_walk(
            StructureAnnouncer(), self.MARKDOWN, ["Intro", "Quill", "the editor", "Lite"]
        )
        assert said[-1] == "Term"

    def test_html_definition_lists_behave_identically(self) -> None:
        said = _list_walk(
            StructureAnnouncer(), self.HTML, ["Intro", "Quill", "the editor"], markup="html"
        )
        assert said[1:] == ["Definition list, 2 terms", "Definition"]
