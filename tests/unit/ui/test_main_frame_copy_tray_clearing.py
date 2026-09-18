"""Clearing the copy tray asks *and* counts (bad.md C9, P3.5).

QUILL asked without a count and QuillLite counted without asking, and each half
is the one the other needed: a count after the fact tells you what you have
lost, and a question without one asks you to confirm you do not know what. The
two editors now do both, from the same wording.

The third case is the one that was silently wrong in QUILL: clearing an already
empty tray asked a warning question and then announced a successful clearing,
which is the same sentence the destructive case produces. Nothing was lost and
the listener could not tell.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.copy_tray import CopyTray  # noqa: E402
from quill.ui.main_frame_copy_tray import CopyTrayMixin  # noqa: E402


class _Host(CopyTrayMixin):
    """Just the surface CopyTrayMixin.clear_all_tray_slots reaches for."""

    def __init__(self, tmp_path: Path, *, answer: int, filled: int = 0) -> None:
        self._copy_tray_instance = CopyTray(tmp_path)
        for number in range(1, filled + 1):
            self._copy_tray_instance.copy_to(number, f"clip {number}")
        self._answer = answer
        self.frame = None
        self.announced: list[str] = []
        self.status: list[str] = []
        self.asked: list[str] = []

    def _show_modal_dialog(self, dialog: object, title: str) -> int:
        self.asked.append(getattr(dialog, "GetMessage", lambda: title)())
        return self._answer

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _update_paste_tray_labels(self) -> None:
        pass

    def _refresh_statusbar(self) -> None:
        pass


@pytest.fixture(scope="module")
def _app():
    app = wx.App()
    yield app
    del app


def test_an_empty_tray_is_not_worth_a_question(tmp_path: Path, _app) -> None:
    host = _Host(tmp_path, answer=wx.ID_YES, filled=0)
    host.clear_all_tray_slots()
    assert host.asked == []
    assert host.announced == ["The copy tray is already empty"]


def test_the_question_names_how_many_slots_are_filled(tmp_path: Path, _app) -> None:
    host = _Host(tmp_path, answer=wx.ID_NO, filled=3)
    host.clear_all_tray_slots()
    assert host.asked and "3 filled tray slots" in host.asked[0]


def test_declining_leaves_every_slot_alone(tmp_path: Path, _app) -> None:
    host = _Host(tmp_path, answer=wx.ID_NO, filled=3)
    host.clear_all_tray_slots()
    assert not host._tray().slot(1).is_empty()
    assert host.announced == ["The copy tray was left alone"]


def test_clearing_says_how_many_it_cleared(tmp_path: Path, _app) -> None:
    host = _Host(tmp_path, answer=wx.ID_YES, filled=3)
    host.clear_all_tray_slots()
    assert host._tray().slot(1).is_empty()
    assert host.announced == ["Cleared 3 tray slots"]


def test_one_slot_is_said_in_the_singular(tmp_path: Path, _app) -> None:
    host = _Host(tmp_path, answer=wx.ID_YES, filled=1)
    host.clear_all_tray_slots()
    assert host.announced == ["Cleared 1 tray slot"]
    assert "1 filled tray slot?" in host.asked[0]
