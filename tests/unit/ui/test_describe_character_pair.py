"""Describe Character is two commands, as it is in QUILL Lite (bad.md P1.13).

QUILL had one: `Ctrl+Shift+C` opened a modal dialog with the full description.
That is the right answer to "what *exactly* is this character" and the wrong
answer to the question people actually press it for -- "is that a hyphen or an
en dash?" -- which wants a sentence spoken where you stand, not a window to
open, read and close.

QUILL Lite already split them, and this is the split: the summary is spoken on
`Ctrl+Shift+C`, and the detail keeps its readable window one key along on
`Ctrl+Alt+C`. Nothing is lost -- the dialog is still there, and it is still the
same shared `quill.core.char_describe` behind both.
"""

from __future__ import annotations

import pytest

from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui.main_frame_classic_editor import ClassicEditorMixin


class _Editor:
    def __init__(self, text: str, caret: int) -> None:
        self._text = text
        self._caret = caret

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._caret


class _Host(ClassicEditorMixin):
    def __init__(self, text: str = "a–b", caret: int = 1) -> None:
        self.editor = _Editor(text, caret)
        self.frame = None
        self.announced: list[str] = []
        self.status: list[str] = []
        self.modals: list[str] = []

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _show_modal_dialog(self, dialog: object, title: str) -> int:
        self.modals.append(title)
        return 0


def test_the_summary_is_spoken_and_nothing_opens() -> None:
    host = _Host()
    host.describe_character()
    assert host.modals == []
    # _set_status is the speaking one on MainFrame: it says the line AND leaves
    # it in the status bar to be read again. Announcing beside it would say the
    # same sentence twice, which is what test_no_double_announce guards.
    assert host.status and "En dash" in host.status[0]
    assert host.announced == []


def test_the_end_of_the_document_is_an_answer_not_an_error() -> None:
    host = _Host(text="ab", caret=2)
    host.describe_character()
    assert host.status == ["End of document (no character at the cursor)"]


def test_the_detail_still_opens_its_readable_window() -> None:
    wx = pytest.importorskip("wx")
    app = wx.App()
    try:
        host = _Host()
        host.describe_character_detail()
        assert host.modals == ["Character at Cursor"]
    finally:
        del app


def test_the_pair_uses_quilllites_two_chords() -> None:
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    assert DEFAULT_KEYMAP["power.describe_character"] == lite["cmd_describe_character"]
    assert (
        DEFAULT_KEYMAP["power.describe_character_detail"] == lite["cmd_describe_character_detail"]
    )


def test_the_detail_command_is_registered_where_the_palette_can_find_it() -> None:
    from quill.ui.main_frame_power_tools_menu import POWER_TOOLS_COMMANDS

    ids = {command.id for command in POWER_TOOLS_COMMANDS}
    assert "power.describe_character_detail" in ids


@pytest.mark.parametrize(
    "command_id", ["power.describe_character", "power.describe_character_detail"]
)
def test_both_are_tagged_for_the_feature_map(command_id: str) -> None:
    from quill.core.feature_command_map import COMMAND_FEATURE_MAP

    assert command_id in COMMAND_FEATURE_MAP
