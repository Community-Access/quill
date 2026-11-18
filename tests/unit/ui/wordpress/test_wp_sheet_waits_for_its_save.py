"""A Properties sheet stays open until its save has landed (UX review item 32).

It used to close on OK the moment the save was sent, so a failure, or Cancel
on "Changed on the Site", lost every edit on it.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.workbench.properties import FieldSpec, PageSpec, SheetSpec, SheetState  # noqa: E402
from quill.ui import workbench_sheet_editor as editor_mod  # noqa: E402
from quill.ui.workbench_sheet_editor import PENDING, WorkbenchSheetEditor  # noqa: E402

SHEET = SheetSpec(
    "thing", "Thing Properties", (PageSpec("general", "General", (FieldSpec("name", "Name"),)),)
)


def _editor(on_save: Any) -> WorkbenchSheetEditor:
    return WorkbenchSheetEditor(
        wx.Frame(None),
        SHEET,
        {"name": "One"},
        title="Thing Properties",
        copy_text=lambda _t: None,
        on_save=on_save,
    )


def _ended(sheet: WorkbenchSheetEditor, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    codes: list[int] = []
    monkeypatch.setattr(sheet.dialog, "EndModal", codes.append)
    monkeypatch.setattr(editor_mod, "dialog_alive", lambda _d: True)
    return codes


def test_ok_waits_and_a_failed_save_keeps_the_sheet_and_its_edits(
    wx_session_app, monkeypatch
) -> None:
    sent: list[str] = []

    def on_save(state: SheetState) -> str:
        sent.append(str(state.pending()[0].after))
        return PENDING

    sheet = _editor(on_save)
    codes = _ended(sheet, monkeypatch)
    sheet.controls["name"].ChangeValue("Two")
    sheet._save(close=True)
    ok, apply = sheet._save_buttons
    assert sent == ["Two"] and codes == [] and not ok.IsEnabled() and not apply.IsEnabled()
    sheet.save_finished(False)
    assert codes == [] and ok.IsEnabled()
    assert sheet.controls["name"].GetValue() == "Two"  # the edit is still there to try again
    sheet._save(close=True)
    sheet.save_finished(True)
    assert codes == [wx.ID_OK]
    sheet.dialog.Destroy()


def test_apply_waits_then_keeps_the_sheet_on_what_was_saved(wx_session_app, monkeypatch) -> None:
    sheet = _editor(lambda _state: PENDING)
    codes = _ended(sheet, monkeypatch)
    sheet.controls["name"].ChangeValue("Two")
    sheet._save(close=False)
    sheet.save_finished(True)
    assert codes == [] and sheet.state.loaded["name"] == "Two" and not sheet.collect().pending()
    sheet.dialog.Destroy()


def test_a_sheet_closed_while_saving_ignores_the_late_answer(wx_session_app, monkeypatch) -> None:
    sheet = _editor(lambda _state: PENDING)
    sheet.controls["name"].ChangeValue("Two")
    sheet._save(close=True)
    monkeypatch.setattr(editor_mod, "dialog_alive", lambda _d: False)
    sheet.save_finished(True)  # nothing to close, nothing raised
    sheet.dialog.Destroy()
