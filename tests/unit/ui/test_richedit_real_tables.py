r"""Real tables in rich text, through the real Rich Edit control.

In a rich document Insert Table makes RichEdit's own table -- a grid on screen
and a table to a screen reader -- and the table keys, Tab and the row and column
edits work on it (quill.ui.richedit_tables, quill.core.native_tables). A fake
control cannot see any of what matters here: the row and cell marks RichEdit
counts in every caret position and leaves out of ``GetValue``, what
``EM_SETTEXTEX`` does with an RTF fragment, and what ``ITextDocument::Save``
writes.

Skips where the native control is not (no Windows, no comtypes). It creates the
control in a hidden frame and sends no input.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core import native_tables, table_nav
from quill.ui import richedit_tables


@pytest.fixture()
def rich(wx_session_app):
    from quill.ui.richedit_rtf_surface import create_richedit_rtf

    frame = wx.Frame(None)
    control = create_richedit_rtf(wx, frame, wx.TE_MULTILINE)
    wrapper = getattr(control, "quill_richedit", None)
    if wrapper is None or not wrapper.rtf_available():
        frame.Destroy()
        pytest.skip("no native Rich Edit / TOM on this build")
    wrapper.set_text_mode("rich")
    yield control, wrapper
    frame.Destroy()
    wx_session_app.Yield()


def _grid(control) -> table_nav.TableGrid:
    text = control.GetValue()
    grid = table_nav.find_table_at(text, text.index(native_tables.ROW_START) + 1)
    assert grid is not None and grid.native
    return grid


def _cells(grid: table_nav.TableGrid) -> list[list[str]]:
    return [[cell.text for cell in row] for row in grid.rows]


def test_insert_table_makes_a_real_table_and_lands_in_its_first_cell(rich) -> None:
    control, _wrapper = rich
    control.SetValue("Before")
    control.SetInsertionPointEnd()
    first = richedit_tables.insert_native_table(control, 2, 3, header=True)
    text = control.GetValue()
    assert len(text) == control.GetLastPosition()  # one character per position
    assert text.startswith("Before\n")  # the table went on a line of its own
    grid = _grid(control)
    assert _cells(grid) == [["Column 1", "Column 2", "Column 3"], ["", "", ""], ["", "", ""]]
    assert first == grid.rows[0][0].offset
    # Typing at a cell's offset lands in that cell: positions really line up.
    control.SetInsertionPoint(grid.rows[1][1].offset)
    control.WriteText("Lead")
    assert _cells(_grid(control))[1] == ["", "Lead", ""]


def test_the_table_keys_and_tab_move_through_it(rich) -> None:
    control, _wrapper = rich
    control.SetValue("")
    richedit_tables.insert_native_table(control, 1, 2, header=True)
    grid = _grid(control)
    step = table_nav.tab_move(control.GetValue(), grid.rows[0][0].offset)
    assert step is not None and step.offset == grid.rows[0][1].offset
    # Tab in the last cell adds a real row, as in Word.
    last = grid.rows[-1][-1].offset
    step = table_nav.tab_move(control.GetValue(), last)
    assert step is not None and step.add_row and step.announcement == "Added row 3, column 1"
    landing = richedit_tables.native_tab_add_row(control, control.GetValue(), last)
    grown = _grid(control)
    assert grown.row_count == 3
    assert landing == grown.rows[2][0].offset


def test_row_and_column_edits_rebuild_the_table_in_place(rich) -> None:
    control, _wrapper = rich
    control.SetValue("")
    richedit_tables.insert_native_table(control, 1, 2, header=True)
    grid = _grid(control)
    control.SetInsertionPoint(grid.rows[1][0].offset)
    control.WriteText("Ann")
    text, caret = control.GetValue(), _grid(control).rows[1][0].offset
    edit = richedit_tables.native_edit(control, text, caret, "insert_column_right")
    assert edit is not None and edit.replacement is not None
    assert _cells(_grid(control)) == [["Column 1", "", "Column 2"], ["Ann", "", ""]]
    text = control.GetValue()
    edit = richedit_tables.native_edit(
        control, text, _grid(control).rows[1][0].offset, "delete_row"
    )
    assert edit is not None
    assert _grid(control).row_count == 1
    tidy = richedit_tables.native_edit(
        control, control.GetValue(), _grid(control).rows[0][0].offset, "tidy_table"
    )
    assert tidy is not None and tidy.replacement is None  # a real table is already lined up


def test_saved_rtf_has_a_real_table_with_its_header_row(rich, tmp_path: Path) -> None:
    control, wrapper = rich
    control.SetValue("")
    richedit_tables.insert_native_table(control, 1, 2, header=True)
    path = tmp_path / "t.rtf"
    wrapper.save_rtf(str(path))
    saved = path.read_bytes().decode("latin-1")
    assert saved.count("\\trowd") == 2 and saved.count("\\trhdr") == 1
    assert "|" not in saved.split("\\trowd", 1)[1]  # no pipe rows on disk
    # Handed out as pipe rows (Save as Word, the switch to Markdown read those).
    handed = bytes(wrapper.get_rtf()).decode("latin-1")
    assert "| --- | --- |" in handed and "\\trowd" not in handed


def test_pipe_rows_open_as_a_real_table(rich) -> None:
    control, wrapper = rich
    rtf = (
        "{\\rtf1\\ansi\\deff0 \\pard Intro\\par | Name | Role |\\par"
        " | --- | --- |\\par | Ann | Lead |\\par After\\par}"
    )
    wrapper.set_rtf(rtf.encode("latin-1"))
    assert _cells(_grid(control)) == [["Name", "Role"], ["Ann", "Lead"]]
    assert "|" not in control.GetValue()


def test_the_arrows_land_on_real_cells_in_the_real_control(rich) -> None:
    control, _wrapper = rich
    control.SetValue("Intro")
    control.SetInsertionPointEnd()
    richedit_tables.insert_native_table(control, 1, 2, header=True)
    grid = _grid(control)
    control.SetInsertionPoint(grid.rows[1][1].offset)
    control.WriteText("Lead")
    step = table_nav.arrow_move(control.GetValue(), 1, "down")
    assert step is not None and step.announcement == "Table, 2 rows, 2 columns. Column 1"
    control.SetInsertionPoint(step.offset)
    step = table_nav.arrow_move(control.GetValue(), control.GetInsertionPoint(), "down")
    assert step is not None and step.announcement == "Row 2: blank"
    control.SetInsertionPoint(step.offset)
    step = table_nav.arrow_move(control.GetValue(), control.GetInsertionPoint(), "right")
    assert step is not None and step.announcement == "Column 2, Column 2: Lead"
    control.SetInsertionPoint(step.offset)
    control.WriteText("X")  # typing where the caret landed goes into that cell
    assert _cells(_grid(control))[1] == ["", "XLead"]
