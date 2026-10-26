"""Insert > Table in QUILL Lite (Ctrl+Alt+T, QUILL's command and key)."""

from __future__ import annotations

import pytest

from quill.core.table_nav import find_table_at


@pytest.fixture
def answer_shape(monkeypatch):
    """Answer the three Insert Table questions; None answers cancel."""
    asked: list[object] = []

    def answer(shape):
        def fake(parent, show_modal, show_message):
            asked.append(parent)
            return shape

        monkeypatch.setattr("quill.ui.table_shape_prompt.prompt_table_shape", fake)
        return asked

    return answer


def test_a_markdown_table_is_pipe_rows_the_table_keys_read(lite_window, answer_shape) -> None:
    win = lite_window("", cursor=0, mode="plain")
    win.set_document_language("markdown", announce=False)
    answer_shape((2, 3, True))
    win.cmd_insert_table()
    text = win.control.GetValue()
    assert text == (
        "| Column 1 | Column 2 | Column 3 |\n| --- | --- | --- |\n|  |  |  |\n|  |  |  |\n"
    )
    grid = find_table_at(text, 0)
    assert grid is not None and (grid.row_count, grid.col_count) == (3, 3)
    # Ready to type in the first cell.
    assert win.control.GetInsertionPoint() == 2
    assert win.announcements[-1].startswith(
        "Inserted a table of 2 rows and 3 columns, with a header row."
    )
    assert "moves to the next cell" in win.announcements[-1]


def test_a_rich_text_document_gets_a_real_table(lite_window, answer_shape, monkeypatch) -> None:
    """Rich text gets RichEdit's own table, never pipe rows (the live control's
    side is tests/unit/ui/test_richedit_real_tables.py)."""
    win = lite_window("", cursor=0, mode="rich")
    made: list[tuple[int, int, bool]] = []

    def fake_insert(control, rows, columns, *, header):
        made.append((rows, columns, header))
        return 0

    monkeypatch.setattr("quill.ui.richedit_tables.insert_native_table", fake_insert)
    answer_shape((1, 2, False))
    win.cmd_insert_table()
    assert made == [(1, 2, False)]
    assert "|" not in win.control.GetValue()
    assert win.announcements[-1].startswith("Inserted a table of 1 rows and 2 columns.")
    assert "Tab or" in win.announcements[-1]


def test_an_html_table_marks_its_header_cells_for_screen_readers(lite_window, answer_shape) -> None:
    win = lite_window("", cursor=0, mode="plain")
    win.set_document_language("html", announce=False)
    answer_shape((1, 2, True))
    win.cmd_insert_table()
    text = win.control.GetValue()
    assert text.count('<th scope="col">') == 2
    assert "<td></td>" in text
    caret = win.control.GetInsertionPoint()
    assert text[:caret].endswith('<th scope="col">')
    # The table keys read pipe rows, so an HTML table does not promise them.
    assert "next cell" not in win.announcements[-1]


def test_a_table_starts_on_a_line_of_its_own(lite_window, answer_shape) -> None:
    win = lite_window("Notes", cursor=5, mode="plain")
    win.set_document_language("markdown", announce=False)
    answer_shape((1, 1, False))
    win.cmd_insert_table()
    assert win.control.GetValue() == "Notes\n|  |\n"
    assert win.control.GetInsertionPoint() == len("Notes\n") + 2


def test_cancelling_inserts_nothing(lite_window, answer_shape) -> None:
    win = lite_window("keep", cursor=4, mode="plain")
    asked = answer_shape(None)
    win.cmd_insert_table()
    assert asked == [win]
    assert win.control.GetValue() == "keep"


def test_insert_table_and_trim_share_quills_keys() -> None:
    """Rule 2: the command both editors have keeps the chord."""
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    keys = {handler: key for _menu, _label, key, handler, _kind in COMMANDS}
    assert keys["cmd_insert_table"] == DEFAULT_KEYMAP["format.insert_table"] == "Ctrl+Alt+T"
    assert (
        keys["cmd_trim_trailing_space"]
        == DEFAULT_KEYMAP["edit.trim_trailing_whitespace"]
        == "Ctrl+Alt+R"
    )
