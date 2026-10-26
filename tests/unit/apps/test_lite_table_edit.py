"""Editing a table in QUILL Lite: Navigate > Table's edits, and Tab between cells."""

from __future__ import annotations

TABLE = "| Name | Role |\n| --- | --- |\n| Ann | Lead |\n"


def _at(text: str, needle: str) -> int:
    return text.index(needle)


def test_insert_row_below_adds_a_blank_row_and_says_so(lite_window) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, "Ann"))
    win.cmd_table_insert_row_below()
    assert win.control.GetValue() == "| Name | Role |\n| --- | --- |\n| Ann | Lead |\n|  |  |\n"
    assert win.announcements[-1] == "Added row 3"
    assert win.modified


def test_insert_column_right_then_delete_it_restores_the_table(lite_window) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, "Ann"))
    win.cmd_table_insert_column_right()
    assert win.control.GetValue().splitlines()[0] == "| Name |  | Role |"
    assert win.announcements[-1] == "Added a column. Column 2 of 3"
    win.cmd_table_delete_column()
    assert win.control.GetValue() == TABLE
    assert win.announcements[-1] == "Deleted column 2. 2 columns left"


def test_delete_row_removes_the_caret_row(lite_window) -> None:
    text = TABLE + "| Bo | Tester |\n"
    win = lite_window(text, cursor=_at(text, "Bo"))
    win.cmd_table_delete_row()
    assert win.control.GetValue() == TABLE
    assert win.announcements[-1] == "Deleted row 3. 2 rows left"


def test_tidy_lines_the_columns_up(lite_window) -> None:
    text = "| N | Role |\n| --- | --- |\n| Annabel | x |\n"
    win = lite_window(text, cursor=0)
    win.cmd_table_tidy()
    assert win.control.GetValue().splitlines() == [
        "| N       | Role |",
        "| ------- | ---- |",
        "| Annabel | x    |",
    ]


def test_an_edit_outside_a_table_says_so_and_changes_nothing(lite_window) -> None:
    win = lite_window("plain text", cursor=2)
    win.cmd_table_insert_row_below()
    assert win.control.GetValue() == "plain text"
    assert win.announcements[-1] == "Not in a table"


def test_tab_moves_to_the_next_cell_and_shift_tab_comes_back(lite_window) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, "Ann"))
    assert win._table_tab(backwards=False) is True
    assert win.control.GetInsertionPoint() == _at(TABLE, "Lead")
    assert win.announcements[-1] == "Column 2, Role: Lead"
    assert win._table_tab(backwards=True) is True
    assert win.control.GetInsertionPoint() == _at(TABLE, "Ann")


def test_tab_in_the_last_cell_adds_a_row(lite_window) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, "Lead"))
    win._table_tab(backwards=False)
    assert win.control.GetValue() == TABLE + "|  |  |\n"
    assert win.announcements[-1] == "Added row 3, column 1"


def test_tab_outside_a_table_is_left_to_the_tab_mode(lite_window) -> None:
    win = lite_window("plain", cursor=2)
    assert win._table_tab(backwards=False) is False


def test_tab_in_a_read_only_table_does_not_add_a_row(lite_window) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, "Lead"))
    win._read_only = True
    win._table_tab(backwards=False)
    assert win.control.GetValue() == TABLE
    assert win.announcements[-1] == "No more cells, end of table"


def test_the_table_edits_are_refused_while_read_only() -> None:
    from quill.core.lite.read_only import TEXT_CHANGING_HANDLERS

    for handler in (
        "cmd_table_insert_row_below",
        "cmd_table_insert_column_right",
        "cmd_table_delete_row",
        "cmd_table_delete_column",
        "cmd_table_tidy",
        "cmd_insert_table",
    ):
        assert handler in TEXT_CHANGING_HANDLERS, handler


# -- the arrows read a table cell by cell (2026-10-26) ---------------------------


class _Arrow:
    """A bare arrow key, as the window's key handler sees it."""

    def __init__(self, code: int, *, shift: bool = False) -> None:
        self.code, self.shift = code, shift

    def GetKeyCode(self) -> int:  # noqa: N802 - wx spelling
        return self.code

    def ControlDown(self) -> bool:  # noqa: N802
        return False

    def AltDown(self) -> bool:  # noqa: N802
        return False

    def ShiftDown(self) -> bool:  # noqa: N802
        return self.shift


def test_down_arrives_in_the_first_cell_and_says_the_shape_once(lite_window) -> None:
    import wx

    text = "Intro\n" + TABLE
    win = lite_window(text, cursor=2)
    assert win._table_arrow(_Arrow(wx.WXK_DOWN)) is True
    assert win.control.GetInsertionPoint() == _at(text, "Name")
    assert win.announcements[-1] == "Table, 2 rows, 2 columns. Name"
    assert win._table_arrow(_Arrow(wx.WXK_DOWN)) is True
    assert win.announcements[-1] == "Row 2: Ann"


def test_right_at_a_cells_end_goes_to_the_next_cell(lite_window) -> None:
    import wx

    win = lite_window(TABLE, cursor=_at(TABLE, "Ann") + 1)
    assert win._table_arrow(_Arrow(wx.WXK_RIGHT)) is False  # inside the word: the editor's
    win.control.SetInsertionPoint(_at(TABLE, "Ann") + 3)
    assert win._table_arrow(_Arrow(wx.WXK_RIGHT)) is True
    assert win.control.GetInsertionPoint() == _at(TABLE, "Lead")
    assert win.announcements[-1] == "Column 2, Role: Lead"


def test_shift_arrows_still_select(lite_window) -> None:
    import wx

    win = lite_window(TABLE, cursor=_at(TABLE, "Ann"))
    assert win._table_arrow(_Arrow(wx.WXK_DOWN, shift=True)) is False
