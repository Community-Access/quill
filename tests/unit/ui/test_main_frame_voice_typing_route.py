"""Tools > Dictation opens Windows' panel the way the voice typing engine does.

The legacy shim (``quill.core.dictation``) is deprecated; ``toggle_dictation``
presses Windows+H through ``launch_windows_dictation`` itself. Fakes only: the
real launcher sends a key to the desktop and must never run in a test.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.platform.windows import dictation as platform_dictation
from quill.ui.main_frame_bw import BwSpeechMixin


class _Host(BwSpeechMixin):
    def __init__(self) -> None:
        self._wx = wx
        self.editor = SimpleNamespace(SetFocus=lambda: None)
        self.status: list[str] = []
        self.boxes: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _show_message_box(self, message: str, *_args: Any) -> int:
        self.boxes.append(message)
        return wx.OK


def test_the_panel_opens_and_closes_through_the_voice_typing_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    presses: list[int] = []
    monkeypatch.setattr(platform_dictation, "launch_windows_dictation", lambda: presses.append(1))
    host = _Host()
    host.toggle_dictation()
    assert presses == [1] and host._voice_typing_open is True
    assert host.status == ["System dictation started. Speak into the editor."]
    host.toggle_dictation()
    assert presses == [1, 1] and host._voice_typing_open is False
    assert host.status[-1] == "System dictation stopped"


def test_a_computer_without_the_panel_says_so_and_stays_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse() -> None:
        raise OSError("Windows dictation is only available on Windows")

    monkeypatch.setattr(platform_dictation, "launch_windows_dictation", refuse)
    host = _Host()
    host.toggle_dictation()
    assert host.boxes == ["System dictation is unavailable on this system."]
    assert getattr(host, "_voice_typing_open", False) is False
