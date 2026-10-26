"""QUILL's table edits and Tab between cells (quill.ui.main_frame_table_nav)."""

from __future__ import annotations

from quill.ui.main_frame_table_nav import _TABLE_ROWS, TableNavMixin

TABLE = "| Name | Role |\n| --- | --- |\n| Ann | Lead |\n"


class _Editor:
    def __init__(self, text: str, caret: int) -> None:
        self.text, self.caret = text, caret

    def GetValue(self) -> str:  # noqa: N802 - wx spelling
        return self.text

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.caret

    def SetInsertionPoint(self, value: int) -> None:  # noqa: N802
        self.caret = value

    def Replace(self, start: int, end: int, value: str) -> None:  # noqa: N802
        self.text = self.text[:start] + value + self.text[end:]


class _Host(TableNavMixin):
    def __init__(self, text: str, caret: int, *, read_only: bool = False) -> None:
        self.editor = _Editor(text, caret)
        self.said: list[str] = []
        self.read_only = read_only

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _document_is_read_only(self) -> bool:
        return self.read_only

    def _refuse_edit_if_read_only(self) -> None:
        if self.read_only:
            raise PermissionError("read-only")


def test_insert_row_below_edits_and_says_so() -> None:
    host = _Host(TABLE, TABLE.index("Ann"))
    host.table_insert_row_below()
    assert host.editor.text == TABLE + "|  |  |\n"
    assert host.said[-1] == "Added row 3"


def test_every_edit_runs_and_tidy_lines_up() -> None:
    host = _Host(TABLE, TABLE.index("Ann"))
    host.table_insert_column_right()
    host.table_delete_column()
    assert host.editor.text == TABLE
    host.table_tidy()
    assert host.editor.text.splitlines()[0] == "| Name | Role |"
    host.editor.text = TABLE + "| Bo | Tester |\n"
    host.editor.caret = host.editor.text.index("Bo")
    host.table_delete_row()
    assert host.editor.text == TABLE


def test_tab_walks_cells_and_adds_a_row_at_the_end() -> None:
    host = _Host(TABLE, TABLE.index("Ann"))
    assert host._table_tab(backwards=False)
    assert host.editor.caret == TABLE.index("Lead")
    assert host._table_tab(backwards=False)
    assert host.editor.text == TABLE + "|  |  |\n"
    assert host.said[-1] == "Added row 3, column 1"


def test_tab_outside_a_table_is_tab() -> None:
    assert _Host("plain", 2)._table_tab(backwards=False) is False


def test_read_only_tab_does_not_add_a_row() -> None:
    host = _Host(TABLE, TABLE.index("Lead"), read_only=True)
    host._table_tab(backwards=False)
    assert host.editor.text == TABLE
    assert host.said[-1] == "No more cells, end of table"


def test_the_table_menu_matches_quill_lites() -> None:
    """Rule 10's other half: QUILL Lite had Navigate > Table and QUILL did not."""
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    lite = [
        COMMAND_EQUIVALENTS[handler]
        for menu, _label, _key, handler, kind in COMMANDS
        if menu == "&Navigate|&Table" and kind != "sep"
    ]
    assert [row[0] for row in _TABLE_ROWS if row[0]] == lite


class _Arrow:
    def __init__(self, code: int) -> None:
        self.code = code

    def GetKeyCode(self) -> int:  # noqa: N802 - wx spelling
        return self.code

    def ControlDown(self) -> bool:  # noqa: N802
        return False

    AltDown = ShiftDown = ControlDown


def test_quill_arrows_move_by_cell_in_a_table() -> None:
    import wx

    host = _Host(TABLE, TABLE.index("Name"))
    host.editor.GetSelection = lambda: (host.editor.caret, host.editor.caret)  # type: ignore[attr-defined]
    assert host._table_arrow(_Arrow(wx.WXK_DOWN)) is True
    assert host.editor.caret == TABLE.index("Ann")
    assert host.said[-1] == "Row 2: Ann"
    # Down from the last row is the editor's again: it leaves the table.
    assert host._table_arrow(_Arrow(wx.WXK_DOWN)) is False
