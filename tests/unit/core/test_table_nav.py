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


def test_describe_position_reads_row_and_column_of_totals() -> None:
    grid, off = _grid()
    assert t.describe_position(grid, 1, 1) == "Row 2 of 3, column 2 of 2"
    # Every landing announcement leads with the same position phrase.
    assert t.move(grid, off, "next").announcement.startswith(t.describe_position(grid, 1, 1))


def test_last_cell_of_table_is_flagged() -> None:
    grid, _ = _grid()
    assert t.is_last_cell(grid, 2, 1)
    assert not t.is_last_cell(grid, 2, 0)
    assert not t.is_last_cell(grid, 1, 1)


def test_edge_at_the_final_cell_says_end_of_table() -> None:
    grid, _ = _grid()
    jones = _DOC.index("Jones")  # last row, last column
    assert t.move(grid, jones, "next") == t.Move(None, "No more cells, end of table")
    assert t.move(grid, jones, "down") == t.Move(None, "No more rows, end of table")
    # A row edge that is not the table edge keeps the plain wording.
    assert t.move(grid, _DOC.index("Smith"), "next") == t.Move(None, "No more cells")


# --------------------------------------------------------------------------- #
# Escaped pipes: what the Word importers emit for a cell containing "|".
# --------------------------------------------------------------------------- #
_ESCAPED = (
    "\n".join([
        r"| Name | Size \| Units | Notes |",
        r"| --- | --- | --- |",
        r"| Alpha | 3 | ok |",
    ])
    + "\n"
)


def test_escaped_pipe_does_not_split_a_cell() -> None:
    grid = t.find_table_at(_ESCAPED, _ESCAPED.index("Alpha"))
    assert grid is not None
    assert grid.col_count == 3  # not 4: the "\|" is cell text, not a divider
    assert [c.text for c in grid.rows[0]] == ["Name", "Size | Units", "Notes"]
    assert [c.text for c in grid.rows[1]] == ["Alpha", "3", "ok"]


def test_escaped_pipe_cell_announces_unescaped_and_aligns_columns() -> None:
    grid = t.find_table_at(_ESCAPED, _ESCAPED.index("Alpha"))
    assert grid is not None
    up = t.move(grid, _ESCAPED.index("3"), "up")
    assert up.announcement == "Row 1 of 2, column 2 of 3: Size | Units"
    # The caret lands on the cell's own text, not on the escape.
    assert up.offset is not None
    assert _ESCAPED[up.offset :].startswith("Size")


def test_escaped_backslash_is_unescaped_in_cell_text() -> None:
    # Two literal backslashes in the document text are one in the cell.
    doc = "\n".join([r"| path | note |", r"| --- | --- |", r"| C:\\tmp | x |"]) + "\n"
    grid = t.find_table_at(doc, doc.index("x"))
    assert grid is not None
    assert grid.rows[1][0].text == r"C:\tmp"


def test_a_line_whose_only_pipe_is_escaped_is_not_a_table_row() -> None:
    doc = (
        "\n".join([
            r"Prose with an escaped \| pipe.",
            r"| aa | bb |",
            r"| --- | --- |",
            r"| cc | dd |",
        ])
        + "\n"
    )
    grid = t.find_table_at(doc, doc.index("cc"))
    assert grid is not None
    assert grid.row_count == 2  # the prose line above is not absorbed
    assert grid.rows[0][0].text == "aa"
