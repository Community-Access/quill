"""Review item 28: a choice in a Workbench sheet is shown by name, saved as its code."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.wordpress.workbench_sheets import sheet_for  # noqa: E402
from quill.ui.workbench_sheet_editor import WorkbenchSheetEditor  # noqa: E402


def test_the_week_choice_shows_days_and_saves_the_number(wx_session_app) -> None:
    row = WbRow(
        "setting",
        "Site",
        "start_of_week",
        {"setting": "First day of the week", "value": "Monday"},
        "",
        raw={"key": "start_of_week", "value": 1},
    )
    sheet = sheet_for(row)
    saved: list[object] = []
    frame = wx.Frame(None)
    try:
        sheet_editor = WorkbenchSheetEditor(
            frame,
            sheet,
            {"label": "First day of the week", "value": 1},
            title="First day of the week Properties",
            copy_text=lambda _t: None,
            on_save=lambda state: saved.append(state.edited.get("value")) or True,
        )
        choice = sheet_editor.controls["value"]
        assert choice.GetStringSelection() == "Monday"
        assert "1" not in [choice.GetString(i) for i in range(choice.GetCount())]
        choice.SetStringSelection("Saturday")
        assert sheet_editor.value_of(sheet.field("value")) == "6"
        sheet_editor.dialog.Destroy()
    finally:
        frame.Destroy()
