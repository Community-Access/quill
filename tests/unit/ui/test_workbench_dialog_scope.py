"""GH-R-002: a Workbench dialog blocks only the Workbench, never the editor.

wx's ShowModal disables every top-level window in the app. Checked on Windows
with wx 4.3.2 on 2026-11-19: a dialog parented to the Workbench left the
editor disabled until it closed. A window marked ``_quill_modal_scope`` now
has its dialogs leave every window outside their own parent chain usable.
"""

from __future__ import annotations

import pytest

from quill.ui.modal_scope import scoped_modal_bystanders


class _Win:
    def __init__(self, parent: _Win | None = None, *, top: bool = True, enabled: bool = True):
        self._parent = parent
        self._top = top
        self._enabled = enabled

    def IsTopLevel(self) -> bool:
        return self._top

    def GetParent(self) -> _Win | None:
        return self._parent

    def IsEnabled(self) -> bool:
        return self._enabled


def test_an_ordinary_dialog_keeps_wx_behaviour() -> None:
    editor = _Win()
    other = _Win()
    dialog = _Win(editor)
    assert scoped_modal_bystanders(dialog, [editor, other, dialog]) == []


def test_a_workbench_dialog_leaves_the_editor_usable() -> None:
    editor = _Win()
    bench = _Win()
    bench._quill_modal_scope = True  # type: ignore[attr-defined]
    dialog = _Win(bench)
    assert scoped_modal_bystanders(dialog, [editor, bench, dialog]) == [editor]


def test_a_dialog_from_a_workbench_dialog_still_blocks_the_whole_chain() -> None:
    editor = _Win()
    bench = _Win()
    bench._quill_modal_scope = True  # type: ignore[attr-defined]
    sheet = _Win(bench)
    picker = _Win(sheet)
    # The sheet and the Workbench stay blocked; only the editor is kept.
    assert scoped_modal_bystanders(picker, [editor, bench, sheet, picker]) == [editor]


def test_a_window_already_disabled_stays_disabled() -> None:
    editor = _Win(enabled=False)
    bench = _Win()
    bench._quill_modal_scope = True  # type: ignore[attr-defined]
    dialog = _Win(bench)
    assert scoped_modal_bystanders(dialog, [editor, bench, dialog]) == []


def test_a_control_inside_the_workbench_is_walked_up_to_it() -> None:
    bench = _Win()
    bench._quill_modal_scope = True  # type: ignore[attr-defined]
    panel = _Win(bench, top=False)
    editor = _Win()
    dialog = _Win(panel)
    assert scoped_modal_bystanders(dialog, [editor, bench, dialog]) == [editor]


def test_on_a_real_modal_loop_the_editor_stays_enabled(wx_session_app: object) -> None:
    wx = pytest.importorskip("wx")
    from quill.ui.dialog_contract import show_modal_dialog

    editor = wx.Frame(None, title="Editor")
    bench = wx.Frame(None, title="Workbench")
    bench._quill_modal_scope = True
    editor.Show()
    bench.Show()
    seen: dict[str, bool] = {}
    dialog = wx.Dialog(bench, title="Sheet")

    def probe() -> None:
        seen["editor"] = editor.IsEnabled()
        seen["bench"] = bench.IsEnabled()
        dialog.EndModal(wx.ID_OK)

    try:
        wx.CallLater(200, probe)
        show_modal_dialog(dialog, "Sheet")
        assert seen == {"editor": True, "bench": False}
        assert editor.IsEnabled() and bench.IsEnabled()
    finally:
        dialog.Destroy()
        editor.Destroy()
        bench.Destroy()


def test_the_workbench_window_is_marked() -> None:
    from pathlib import Path

    source = Path(__file__).resolve().parents[3] / "quill" / "ui" / "workbench_frame.py"
    assert "self.frame._quill_modal_scope = True" in source.read_text(encoding="utf-8")
