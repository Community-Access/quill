"""The shared sheet editor's masked field: a write-only secret is typed, sent once, then gone.

Used by the QAF Spam page's OOPSpam key and an item's password, and shared with
the GitHub Workbench. The box is a password box that always opens empty, its
accessible name says it is hidden, Copy as Text says "hidden", and once a save
has it the secret is out of the sheet's values and out of the box.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.workbench_qaf_spam_edit import spam_fields  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.wordpress.workbench_sheets import sheet_for  # noqa: E402
from quill.core.workbench.properties import (  # noqa: E402
    FieldKind,
    FieldSpec,
    PageSpec,
    SheetSpec,
    SheetState,
    as_text,
)
from quill.ui.workbench_sheet_editor import WorkbenchSheetEditor  # noqa: E402

SECRET = "sk-live-do-not-say"

SHEET = SheetSpec(
    "thing",
    "Thing Properties",
    (
        PageSpec(
            "general",
            "General",
            (
                FieldSpec("name", "Name"),
                FieldSpec("api_key", "New API key", FieldKind.SECRET, help="Write only."),
            ),
        ),
    ),
)


def _editor(
    app: Any, on_save: Any, values: dict[str, object] | None = None
) -> WorkbenchSheetEditor:
    frame = wx.Frame(None)
    return WorkbenchSheetEditor(
        frame,
        SHEET,
        values or {"name": "One", "api_key": SECRET},
        title="Thing Properties",
        copy_text=lambda _t: None,
        on_save=on_save,
    )


def test_the_secret_box_is_masked_empty_and_named_hidden(wx_session_app) -> None:
    sheet = _editor(wx_session_app, lambda _s: True)
    box = sheet.controls["api_key"]
    assert box.GetWindowStyleFlag() & wx.TE_PASSWORD
    assert box.GetValue() == ""  # never read back, even when the site sent one
    assert WorkbenchSheetEditor.spoken_name(SHEET.field("api_key")) == (
        "New API key, hidden as you type"
    )
    assert SECRET not in sheet.text() and "New API key: hidden" in sheet.text()
    assert "hidden" in as_text(SHEET, {"api_key": SECRET}) and SECRET not in as_text(
        SHEET, {"api_key": SECRET}
    )


def test_apply_sends_the_secret_once_then_forgets_it(wx_session_app) -> None:
    sent: list[dict[str, object]] = []

    def on_save(state: SheetState) -> bool:
        sent.append({c.key: c.after for c in state.pending()})
        return True

    sheet = _editor(wx_session_app, on_save, {"name": "One"})
    sheet.controls["api_key"].ChangeValue("typed-key")
    sheet._save(close=False)
    assert sent == [{"api_key": "typed-key"}]
    assert sheet.controls["api_key"].GetValue() == ""
    assert "api_key" not in sheet.state.loaded and "api_key" not in sheet.state.edited
    sheet._save(close=False)  # nothing typed again: nothing to send
    assert len(sent) == 1


def test_a_refused_save_keeps_the_box_but_not_the_values(wx_session_app) -> None:
    sheet = _editor(wx_session_app, lambda _s: False, {"name": "One"})
    sheet.controls["api_key"].ChangeValue("typed-key")
    sheet._save(close=False)
    assert sheet.controls["api_key"].GetValue() == "typed-key"  # so the person can try again
    assert "api_key" not in sheet.state.edited and "api_key" not in sheet.state.loaded


def test_wordpress_secret_fields_use_the_masked_kind() -> None:
    oopspam = [f for f in spam_fields() if f.key == "qaf_oopspam_key"]
    assert oopspam and oopspam[0].kind is FieldKind.SECRET
    row = WbRow("item", "Site", "1", {}, "Hello", subkind="post", raw={"type": "post"})
    assert sheet_for(row).field("password").kind is FieldKind.SECRET
