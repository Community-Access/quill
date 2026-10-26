"""Editing pipe tables (quill.core.table_edit) and Tab in a table (table_nav)."""

from __future__ import annotations

from quill.core import table_edit, table_nav

TABLE = "Intro\n| Name | Role |\n| --- | :---: |\n| Ann | Lead |\n| Bo | Tester |\nAfter\n"


def _apply(text: str, edit: table_edit.TableEdit) -> str:
    assert edit.replacement is not None, edit.announcement
    return text[: edit.start] + edit.replacement + text[edit.end :]


def _at(text: str, needle: str) -> int:
    return text.index(needle)


def test_insert_row_below_adds_a_blank_row_and_lands_in_it() -> None:
    edit = table_edit.insert_row_below(TABLE, _at(TABLE, "Ann"))
    out = _apply(TABLE, edit)
    assert out == (
        "Intro\n| Name | Role |\n| --- | :---: |\n| Ann | Lead |\n|  |  |\n| Bo | Tester |\nAfter\n"
    )
    grid = table_nav.find_table_at(out, edit.caret)
    assert grid is not None and table_nav.locate_cell(grid, edit.caret) == (2, 0)
    assert edit.announcement == "Added row 3"


def test_a_row_inserted_under_the_header_is_a_body_row() -> None:
    out = _apply(TABLE, table_edit.insert_row_below(TABLE, _at(TABLE, "Name")))
    assert out.splitlines()[1:4] == ["| Name | Role |", "| --- | :---: |", "|  |  |"]


def test_delete_row_keeps_the_rest_and_says_how_many_are_left() -> None:
    edit = table_edit.delete_row(TABLE, _at(TABLE, "Bo"))
    assert _apply(TABLE, edit) == "Intro\n| Name | Role |\n| --- | :---: |\n| Ann | Lead |\nAfter\n"
    assert edit.announcement == "Deleted row 3. 2 rows left"


def test_the_last_body_row_of_a_header_table_can_go_but_not_the_table() -> None:
    small = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    after = _apply(small, table_edit.delete_row(small, _at(small, "1")))
    assert after == "| A | B |\n| --- | --- |\n"
    refused = table_edit.delete_row(after, _at(after, "A"))
    assert refused.replacement is None and "two rows" in refused.announcement


def test_insert_column_right_keeps_alignment_and_header() -> None:
    edit = table_edit.insert_column_right(TABLE, _at(TABLE, "Name"))
    out = _apply(TABLE, edit)
    assert out.splitlines()[1:3] == ["| Name |  | Role |", "| --- | --- | :---: |"]
    assert out.splitlines()[3] == "| Ann |  | Lead |"
    assert edit.announcement == "Added a column. Column 2 of 3"


def test_delete_column_names_the_header_it_removed() -> None:
    edit = table_edit.delete_column(TABLE, _at(TABLE, "Lead"))
    out = _apply(TABLE, edit)
    assert out.splitlines()[1:4] == ["| Name |", "| --- |", "| Ann |"]
    assert edit.announcement == "Deleted column 2, Role. 1 columns left"


def test_tidy_pads_every_column_to_its_widest_cell() -> None:
    out = _apply(TABLE, table_edit.tidy_table(TABLE, _at(TABLE, "Ann")))
    assert out.splitlines()[1:5] == [
        "| Name | Role   |",
        "| ---- | :----: |",
        "| Ann  | Lead   |",
        "| Bo   | Tester |",
    ]
    # Still the same table to the keys.
    grid = table_nav.find_table_at(out, _at(out, "Tester"))
    assert grid is not None and grid.cell(2, 1).text == "Tester"


def test_a_pipe_in_a_cell_survives_an_edit() -> None:
    text = "| A | B |\n| --- | --- |\n| x \\| y | 2 |\n"
    out = _apply(text, table_edit.tidy_table(text, 0))
    grid = table_nav.find_table_at(out, 0)
    assert grid is not None and grid.cell(1, 0).text == "x | y"


def test_outside_a_table_nothing_changes() -> None:
    for edit in (
        table_edit.insert_row_below(TABLE, 1),
        table_edit.delete_row(TABLE, 1),
        table_edit.insert_column_right(TABLE, 1),
        table_edit.delete_column(TABLE, 1),
        table_edit.tidy_table(TABLE, 1),
    ):
        assert edit.replacement is None and edit.announcement == "Not in a table"


# -- column headers and Tab (quill.core.table_nav) ---------------------------


def test_a_new_column_says_its_header_and_the_same_column_does_not() -> None:
    grid = table_nav.find_table_at(TABLE, _at(TABLE, "Ann"))
    assert grid is not None and grid.header
    across = table_nav.move(grid, _at(TABLE, "Ann"), "next")
    assert across.announcement == "Column 2, Role: Lead"
    down = table_nav.move(grid, _at(TABLE, "Lead"), "down")
    assert down.announcement == "Row 3: Tester"


def test_a_table_without_a_separator_has_no_header_to_say() -> None:
    text = "| a | b |\n| c | d |\n"
    grid = table_nav.find_table_at(text, 0)
    assert grid is not None and not grid.header
    assert table_nav.move(grid, 2, "next").announcement == "Column 2: b"


def test_tab_walks_cells_and_wraps_to_the_next_row() -> None:
    step = table_nav.tab_move(TABLE, _at(TABLE, "Lead"))
    assert step is not None and step.insert is None
    assert TABLE[step.offset :].startswith("Bo")
    back = table_nav.tab_move(TABLE, _at(TABLE, "Bo"), backwards=True)
    assert back is not None and TABLE[back.offset :].startswith("Lead")


def test_tab_in_the_last_cell_adds_a_row() -> None:
    step = table_nav.tab_move(TABLE, _at(TABLE, "Tester"))
    assert step is not None and step.insert is not None
    position, inserted = step.insert
    out = TABLE[:position] + inserted + TABLE[position:]
    assert out.endswith("| Bo | Tester |\n|  |  |\nAfter\n")
    grid = table_nav.find_table_at(out, step.offset)
    assert grid is not None and table_nav.locate_cell(grid, step.offset) == (3, 0)
    assert step.announcement == "Added row 4, column 1"


def test_shift_tab_in_the_first_cell_stays() -> None:
    step = table_nav.tab_move(TABLE, _at(TABLE, "Name"), backwards=True)
    assert step is not None and step.offset is None
    assert step.announcement == "No more cells, start of table"


def test_tab_outside_a_table_is_none() -> None:
    assert table_nav.tab_move(TABLE, 1) is None


def test_arrow_move_reads_a_real_table_too() -> None:
    from quill.core.table_nav import arrow_move

    text = "Intro\n￹\nName\tRole\t￻\n￹\nAnn\tLead\t￻\nAfter"
    arrived = arrow_move(text, 2, "down")
    assert arrived is not None and arrived.announcement == "Table, 2 rows, 2 columns. Name"
    below = arrow_move(text, arrived.offset, "down")
    assert below is not None and below.announcement == "Row 2: Ann"
    assert text[below.offset : below.offset + 3] == "Ann"
    left = arrow_move(text, below.offset, "left")  # the row's start: the row above's last cell
    assert left is not None and left.announcement == "Row 1, column 2: Role"
    assert arrow_move(text, 2, "left") is None  # outside the table, the editor's
