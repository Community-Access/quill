"""Cell-by-cell navigation over a pipe table in document text."""

from __future__ import annotations

from quill.core import table_nav as t

_DOC = (
    "Some intro text.\n"
    "| First Name | Last Name |\n"
    "| --- | --- |\n"
    "| Alice | Smith |\n"
    "| Bob | Jones |\n"
    "After the table.\n"
)


def _grid():
    off = _DOC.index("Alice")
    return t.find_table_at(_DOC, off), off


def test_finds_table_and_excludes_separator() -> None:
    grid, _ = _grid()
    assert grid is not None
    assert grid.row_count == 3  # header + two body rows; separator dropped
    assert grid.col_count == 2
    assert grid.cell(0, 0).text == "First Name"
    assert grid.cell(2, 1).text == "Jones"


def test_no_table_outside_it() -> None:
    assert t.find_table_at(_DOC, _DOC.index("intro")) is None
    assert t.find_table_at(_DOC, _DOC.index("After")) is None


def test_next_and_previous_cell_in_row() -> None:
    grid, off = _grid()
    assert t.move(grid, off, "next").announcement == "Row 2 of 3, column 2 of 2: Smith"
    smith = _DOC.index("Smith")
    assert t.move(grid, smith, "previous").announcement == "Row 2 of 3, column 1 of 2: Alice"
    # Edge: no cell to the right of the last column.
    assert t.move(grid, smith, "next") == t.Move(None, "No more cells")


def test_up_and_down_cell_in_column() -> None:
    grid, off = _grid()
    assert t.move(grid, off, "down").announcement == "Row 3 of 3, column 1 of 2: Bob"
    assert t.move(grid, _DOC.index("First"), "up") == t.Move(None, "No more rows")
    assert t.move(grid, _DOC.index("Bob"), "down") == t.Move(None, "No more rows")


def test_row_and_table_ends() -> None:
    grid, off = _grid()  # in Alice (row 1, col 0)
    assert t.move(grid, off, "row_end").announcement.endswith("Smith")
    assert t.move(grid, _DOC.index("Smith"), "row_start").announcement.endswith("Alice")
    assert t.move(grid, off, "table_start").announcement.endswith("First Name")
    assert t.move(grid, off, "table_end").announcement == "Row 3 of 3, column 2 of 2: Jones"


def test_blank_cell_says_blank() -> None:
    doc = "| A | |\n| --- | --- |\n| x | |\n"
    grid = t.find_table_at(doc, doc.index("x"))
    assert grid is not None
    assert t.move(grid, doc.index("x"), "next").announcement.endswith(": blank")


def test_single_pipe_line_is_not_a_table() -> None:
    assert t.find_table_at("a | b only one line\n", 3) is None
