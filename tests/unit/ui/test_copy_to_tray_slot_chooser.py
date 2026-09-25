"""Copy to Tray Slot... in QUILL (bad.md P2.1, 5.1).

QUILL could copy to the *next free* slot (`Ctrl+Alt+Y`) or to a slot by its own
chord, and that is the whole point of the chooser QUILL Lite has on
`Alt+Shift+Y`: a tray you fill in order is a tray whose numbers mean nothing,
and the value of a numbered slot is that you chose the number and can therefore
remember it.

Each row says what it would overwrite, because overwriting something put there
deliberately is the one mistake this feature can make -- and a listener cannot
see the tray to check first.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.copy_tray import CopyTray  # noqa: E402
from quill.ui.main_frame_copy_tray import CopyTrayMixin  # noqa: E402


class _Chooser:
    """Stands in for wx.SingleChoiceDialog: records what it was offered."""

    def __init__(self, *args, **kwargs) -> None:
        self.message, self.title, self.choices = args[1], args[2], args[3]
        self.selection = 0

    def __enter__(self) -> _Chooser:
        return self

    def __exit__(self, *_exc) -> bool:
        return False

    def GetSelection(self) -> int:
        return self.selection


class _Host(CopyTrayMixin):
    def __init__(self, tmp_path: Path, *, selection: str, answer: int) -> None:
        self._copy_tray_instance = CopyTray(tmp_path)
        self._selection = selection
        self._answer = answer
        self.frame = None
        self.announced: list[str] = []
        self.status: list[str] = []
        self.offered: list[str] = []
        self.pick = 0

    @property
    def _wx(self):
        host = self

        class _Namespace:
            ID_OK = wx.ID_OK
            NOT_FOUND = wx.NOT_FOUND

            @staticmethod
            def SingleChoiceDialog(*args, **kwargs):
                chooser = _Chooser(*args, **kwargs)
                chooser.selection = host.pick
                host.offered = list(chooser.choices)
                return chooser

        return _Namespace

    def _get_editor_selection(self) -> str:
        return self._selection

    def _show_modal_dialog(self, dialog: object, title: str) -> int:
        return self._answer

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _update_paste_tray_labels(self) -> None:
        pass

    def _refresh_statusbar(self) -> None:
        pass


def test_nothing_selected_is_said_rather_than_offering_a_chooser(tmp_path: Path) -> None:
    host = _Host(tmp_path, selection="", answer=wx.ID_OK)
    host.copy_to_tray_slot()
    assert host.offered == []
    assert host.announced == ["Select something to copy first"]


def test_every_row_says_what_that_slot_holds(tmp_path: Path) -> None:
    host = _Host(tmp_path, selection="new", answer=wx.ID_OK)
    host._tray().copy_to(2, "an earlier clip")
    host.copy_to_tray_slot()
    assert len(host.offered) == host._tray().SLOT_COUNT
    assert host.offered[0] == "Slot 1: empty"
    assert host.offered[1].startswith("Slot 2: an earlier clip")


def test_choosing_an_empty_slot_copies_and_says_so(tmp_path: Path) -> None:
    host = _Host(tmp_path, selection="new", answer=wx.ID_OK)
    host.pick = 0
    host.copy_to_tray_slot()
    assert host._tray().slot(1).preview(40).startswith("new")
    assert host.announced[-1].startswith("Copied to tray slot 1")


def test_choosing_a_filled_slot_says_it_replaced_something(tmp_path: Path) -> None:
    host = _Host(tmp_path, selection="new", answer=wx.ID_OK)
    host._tray().copy_to(3, "older")
    host.pick = 2
    host.copy_to_tray_slot()
    assert host.announced[-1].startswith("Replaced tray slot 3")


def test_cancelling_changes_nothing(tmp_path: Path) -> None:
    host = _Host(tmp_path, selection="new", answer=wx.ID_CANCEL)
    host._tray().copy_to(1, "older")
    host.copy_to_tray_slot()
    assert host._tray().slot(1).preview(40).startswith("older")


def test_it_uses_quilllites_chord() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    assert DEFAULT_KEYMAP["edit.copy_to_tray_slot"] == lite["cmd_copy_to_tray_slot"]
