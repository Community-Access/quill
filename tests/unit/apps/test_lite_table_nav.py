"""Navigate > Table in QUILL Lite: QUILL's cell moves on QUILL's keys (2026-10-17).

Every handler is called here through a lambda, so the coverage gate
(GATE-LITE-COVER) sees the call. The moves themselves are the shared
``quill.core.table_nav`` (tested in tests/unit/core); what is tested here is
QUILL Lite's half: the right cell, the sentence, Go Back, the edges, outside a
table, a Word table opened to edit, and that the keys are QUILL's.
"""

from __future__ import annotations

from typing import Any

import pytest

TABLE = "Team\n\n| Name | Role |\n| --- | --- |\n| Ann | Lead |\n| Bo | Tester |\n\nAfter\n"


def _at(text: str, needle: str) -> int:
    return text.index(needle)


@pytest.mark.parametrize(
    ("start", "move", "landed", "said"),
    [
        ("Name", lambda w: w.cmd_table_next_cell(), "Role", "Column 2: Role"),
        ("Role", lambda w: w.cmd_table_previous_cell(), "Name", "Column 1: Name"),
        ("Name", lambda w: w.cmd_table_cell_below(), "Ann", "Row 2: Ann"),
        ("Lead", lambda w: w.cmd_table_cell_above(), "Role", "Row 1: Role"),
        # A new column in a body row says its header (2026-10-25); the header
        # row's own cells, and moves within one column, do not.
        ("Lead", lambda w: w.cmd_table_row_start(), "Ann", "Column 1, Name: Ann"),
        ("Ann", lambda w: w.cmd_table_row_end(), "Lead", "Column 2, Role: Lead"),
        ("Tester", lambda w: w.cmd_table_first_cell(), "Name", "Row 1, column 1: Name"),
        (
            "Name",
            lambda w: w.cmd_table_last_cell(),
            "Tester",
            "Row 3, column 2, Role: Tester",
        ),
    ],
)
def test_each_move_lands_on_its_cell_and_says_where(
    lite_window, start: str, move: Any, landed: str, said: str
) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, start))
    move(win)
    assert win.control.GetInsertionPoint() == _at(TABLE, landed)
    assert win.announcements[-1] == said


def test_go_back_returns_from_a_cell_move(lite_window) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, "Name"))
    win.cmd_table_last_cell()
    win.cmd_back_location()
    assert win.control.GetInsertionPoint() == _at(TABLE, "Name")


@pytest.mark.parametrize(
    ("start", "move", "said"),
    [
        ("Role", lambda w: w.cmd_table_next_cell(), "No more cells"),
        ("Name", lambda w: w.cmd_table_cell_above(), "No more rows"),
        ("Tester", lambda w: w.cmd_table_next_cell(), "No more cells, end of table"),
    ],
)
def test_an_edge_says_so_and_does_not_move(lite_window, start: str, move: Any, said: str) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, start))
    move(win)
    assert win.control.GetInsertionPoint() == _at(TABLE, start)
    assert win.announcements[-1] == said


def test_outside_a_table_every_key_says_so(lite_window) -> None:
    win = lite_window(TABLE, cursor=_at(TABLE, "After"))
    for move in (
        lambda w: w.cmd_table_next_cell(),
        lambda w: w.cmd_table_previous_cell(),
        lambda w: w.cmd_table_cell_below(),
        lambda w: w.cmd_table_cell_above(),
        lambda w: w.cmd_table_row_start(),
        lambda w: w.cmd_table_row_end(),
        lambda w: w.cmd_table_first_cell(),
        lambda w: w.cmd_table_last_cell(),
    ):
        move(win)
        assert win.announcements[-1] == "Not in a table"
        assert win.control.GetInsertionPoint() == _at(TABLE, "After")


def test_a_word_table_opened_to_edit_is_navigable(lite_window, tmp_path) -> None:
    docx = pytest.importorskip("docx")
    from quill.core.lite.open_prepare import RICH, prepare

    document = docx.Document()
    table = document.add_table(rows=2, cols=2)
    for (row, col), text in {(0, 0): "City", (0, 1): "Pop", (1, 0): "Oslo", (1, 1): "700"}.items():
        table.cell(row, col).text = text
    path = tmp_path / "cities.docx"
    document.save(str(path))
    win = lite_window("")
    # A table is on the fidelity list; this test answers "Edit as Rich Text"
    # (the question itself is tested in test_lite_word.py).
    win._ask_word_fidelity = lambda _path, _findings: "rich"
    assert win._commit_load(path, prepare(path, RICH)) is True
    assert win.editor.mode == RICH
    text = win.control.GetValue()
    win.control.SetInsertionPoint(text.index("City"))
    win.cmd_table_cell_below()
    assert win.announcements[-1] == "Row 2: Oslo"


def test_the_keys_are_quills_keys() -> None:
    """Family rule 2: the command both products have keeps the chord."""
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    rows = {handler: key for _menu, _label, key, handler, _kind in COMMANDS}
    for handler, quill_id in COMMAND_EQUIVALENTS.items():
        if handler.startswith("cmd_table_"):
            assert rows[handler] == DEFAULT_KEYMAP[quill_id], handler
    # Eight moves, and since 2026-10-25 five edits (keyless in both editors).
    assert sum(handler.startswith("cmd_table_") for handler in rows) == 13
