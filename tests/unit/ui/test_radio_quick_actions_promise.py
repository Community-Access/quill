"""Quick Actions in Quill Radio promises only what Radio does.

The shared reorder dialog said "the first action is what Enter does" and "the
first 9 also answer to Ctrl+1 through Ctrl+9". In Radio neither was true: Enter
on a Browse Stations row always plays or opens it, and Ctrl+1..9 are the
WindowManager's keys there. The order shapes the right-click menu and nothing
else, and the "Recording actions" list shaped nothing at all (found
2026-09-25). Cast honours all three, so it keeps the full promise.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.quick_actions import QuickActionOrders
from quill.core.radio.quick_actions import CONTEXT_LABELS, CONTEXTS
from quill.ui.media.quick_actions_dialog import position_text
from quill.ui.radio import quick_actions_command


def test_radio_positions_name_no_key() -> None:
    assert position_text(0, 5, direct_keys=False) == "Position 1 of 5"
    assert position_text(2, 5, direct_keys=False) == "Position 3 of 5"


def test_cast_positions_keep_enter_and_the_ctrl_digits() -> None:
    assert position_text(0, 12) == "Position 1 of 12 -- this is what Enter does"
    assert position_text(2, 12) == "Position 3 of 12 -- Ctrl+3"
    assert position_text(10, 12) == "Position 11 of 12"


def test_radio_offers_only_the_lists_some_menu_applies() -> None:
    offered = [cid for cid, _label in quick_actions_command.offered_contexts(CONTEXT_LABELS)]
    assert offered == ["station", "node"]


def test_radio_opens_the_dialog_without_the_key_promise(monkeypatch: Any) -> None:
    from quill.ui.media import quick_actions_dialog

    seen: dict[str, Any] = {}

    class _Dialog:
        def __init__(self, _parent: object, **kwargs: Any) -> None:
            seen.update(kwargs)

        def show(self) -> None:
            return None

    class _Host:
        _radio_quick_actions = QuickActionOrders.defaults(CONTEXTS)
        frame = None

    monkeypatch.setattr(quick_actions_dialog, "QuickActionsDialog", _Dialog)
    quick_actions_command.open_quick_actions(_Host())
    assert seen["direct_keys"] is False
    assert [cid for cid, _label in seen["context_labels"]] == ["station", "node"]


def _dialog_text(wx: Any, *, direct_keys: bool) -> str:
    from quill.ui.media.quick_actions_dialog import QuickActionsDialog

    dialog = QuickActionsDialog(
        None,
        orders=QuickActionOrders.defaults(CONTEXTS),
        context_labels=quick_actions_command.offered_contexts(CONTEXT_LABELS),
        direct_keys=direct_keys,
    )
    try:
        return " ".join(
            child.GetLabel()
            for child in dialog.dialog.GetChildren()
            if isinstance(child, (wx.StaticText, wx.Button))
        )
    finally:
        dialog.dialog.Destroy()


def test_the_dialog_text_promises_keys_only_where_they_exist() -> None:
    wx = pytest.importorskip("wx")
    app = wx.App()
    try:
        radio = _dialog_text(wx, direct_keys=False)
        assert "Ctrl+1" not in radio
        assert "what Enter does" not in radio
        assert "Make Default" not in radio
        assert "right-click menu" in radio
        cast = _dialog_text(wx, direct_keys=True)
        assert "Ctrl+1" in cast and "what Enter does" in cast
    finally:
        del app
