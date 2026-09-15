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
