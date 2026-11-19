"""GH-R-093: a rebound key follows into Shift+F1, the key list and the Key Describer.

The menus already show the person's key (test_github_workbench_requirement_checks).
Shift+F1 and Alt+Shift+F1 read the same bound keys, and the Workbench's own
Key Describer (Help, Ctrl+Alt+K) says what a key does here without doing it,
including why a key that has a command does nothing right now.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.workbench_window_menu import WORKBENCH_KEYS  # noqa: E402
from quill.core.key_describer import describe  # noqa: E402
from tests.unit.ui.test_github_workbench_requirement_checks import _frame  # noqa: E402

_P = "github.workbench."
CHOSEN = "Ctrl+Alt+Shift+F11"


class _Key:
    """A key event as wx delivers it to EVT_CHAR_HOOK."""

    def __init__(self, code: int, *, ctrl: bool = False, alt: bool = False, shift: bool = False):
        self.code, self.ctrl, self.alt, self.shift = code, ctrl, alt, shift
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx's name
        return self.code

    def ControlDown(self) -> bool:  # noqa: N802
        return self.ctrl

    def AltDown(self) -> bool:  # noqa: N802
        return self.alt

    def ShiftDown(self) -> bool:  # noqa: N802
        return self.shift

    def HasAnyModifiers(self) -> bool:  # noqa: N802
        return self.ctrl or self.alt or self.shift

    def Skip(self) -> None:  # noqa: N802
        self.skipped = True


def test_the_sentence_names_the_command_and_why_it_is_not_now() -> None:
    keys = {f"{_P}merge": "Ctrl+Shift+Enter", f"{_P}keys": "Alt+Shift+F1"}
    labels = {f"{_P}merge": "Merge", f"{_P}keys": "Workbench Keys"}
    assert describe("alt+shift+f1", keys, labels) == "alt+shift+f1: Workbench Keys."
    said = describe(
        "Ctrl+Shift+Enter", keys, labels, why_not={f"{_P}merge": "Select a pull request first."}
    )
    assert said == "Ctrl+Shift+Enter: Merge. Not now: Select a pull request first."
    assert describe("Ctrl+Q", keys, labels) == "Ctrl+Q: nothing here."


def test_the_key_describer_is_on_the_help_menu_with_a_key() -> None:
    assert WORKBENCH_KEYS[f"{_P}key_describer"] == "Ctrl+Alt+K"


def test_the_describer_says_keys_instead_of_doing_them_until_escape(
    wx_session_app, quill_data_dir
) -> None:
    frame, said = _frame()
    try:
        frame.run(f"{_P}key_describer")
        assert frame.describing_keys
        assert said[-1].startswith("Key Describer on.")
        where = frame.current
        assert frame.describe_key(_Key(ord("1"), ctrl=True))  # Ctrl+1 is Inbox: said, not done
        assert said[-1].startswith("Ctrl+1: ")
        assert frame.current == where
        bare = _Key(wx.WXK_SHIFT, shift=True)
        assert frame.describe_key(bare) and bare.skipped
        frame.describe_key(_Key(ord("Q"), ctrl=True, alt=True, shift=True))
        assert said[-1] == "Ctrl+Alt+Shift+Q: nothing here."
        assert frame.describe_key(_Key(wx.WXK_ESCAPE))
        assert not frame.describing_keys and said[-1] == "Key Describer off."
        assert frame.describe_key(_Key(ord("1"), ctrl=True)) is False
    finally:
        frame.frame.Destroy()


def test_a_rebound_key_follows_into_shift_f1_the_key_list_and_the_describer(
    wx_session_app, quill_data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = f"{_P}keys"
    comment = "Ctrl+Alt+Shift+F12"
    assert CHOSEN not in WORKBENCH_KEYS.values() and comment not in WORKBENCH_KEYS.values()
    monkeypatch.setattr(
        "quill.core.keymap.load_keymap", lambda: {command: CHOSEN, f"{_P}comment": comment}
    )
    frame, said = _frame()
    shown: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.workbench_help_dialogs.ActionListDialog.show",
        lambda dialog: shown.append([row.text for row in dialog.rows]) or dialog.dialog.Destroy(),
    )
    try:
        assert f"Workbench Keys: {CHOSEN}" in frame.provider.key_text()
        assert "Workbench Keys: Alt+Shift+F1" not in frame.provider.key_text()
        frame.toggle_key_describer()
        frame.describe_key(_Key(wx.WXK_F11, ctrl=True, alt=True, shift=True))
        assert said[-1] == f"{CHOSEN}: Workbench Keys."
        frame.describe_key(_Key(wx.WXK_F1, alt=True, shift=True))
        assert said[-1] == "Alt+Shift+F1: nothing here."
        frame.toggle_key_describer()
        from quill.ui.workbench_frame import NodeRef

        ref = NodeRef("repository", "issues", "owner/repo")
        assert frame.select(ref)
        if frame.current != ref:
            frame._show_node(ref, remember=True)
        frame.list.Select(0)
        frame.what_can_i_do()
        assert f"Comment..., {comment}" in shown[0]
        assert "Comment..., Ctrl+Shift+M" not in shown[0]
    finally:
        frame.frame.Destroy()
