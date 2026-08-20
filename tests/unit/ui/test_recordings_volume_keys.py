"""Ctrl+Up/Ctrl+Down must change playback volume from inside the modal
Recordings dialog, so a played-back recording can be turned down like a live
stream (the modal otherwise hides the Playback menu's volume shortcuts).

Recording playback runs through the same controller/engine as live radio, so
the handler just drives the shared volume commands. These tests drive the
handler directly against a fake controller (no live wx.App needed).
"""

from __future__ import annotations

import types

from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog


class _FakeState:
    def __init__(self) -> None:
        self.volume_percent = 50
        self.muted = False


class _FakeController:
    def __init__(self) -> None:
        self.state = _FakeState()

    def volume_up(self, step: int = 10) -> None:
        self.state.volume_percent = min(100, self.state.volume_percent + step)

    def volume_down(self, step: int = 10) -> None:
        self.state.volume_percent = max(0, self.state.volume_percent - step)


class _KeyEvent:
    def __init__(self, code: int, *, ctrl: bool, shift: bool = False, alt: bool = False) -> None:
        self._code = code
        self._ctrl = ctrl
        self._shift = shift
        self._alt = alt
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx shape
        return self._code

    def ControlDown(self) -> bool:  # noqa: N802 - wx shape
        return self._ctrl

    def ShiftDown(self) -> bool:  # noqa: N802 - wx shape
        return self._shift

    def AltDown(self) -> bool:  # noqa: N802 - wx shape
        return self._alt

    def Skip(self) -> None:  # noqa: N802 - wx shape
        self.skipped = True


_WXK_UP = 315
_WXK_DOWN = 317
_WXK_LEFT = 314


def _make_dialog() -> tuple[RecordingsManagerDialog, _FakeController, list[str]]:
    dialog = RecordingsManagerDialog.__new__(RecordingsManagerDialog)
    controller = _FakeController()
    announced: list[str] = []
    dialog._wx = types.SimpleNamespace(WXK_UP=_WXK_UP, WXK_DOWN=_WXK_DOWN)
    dialog._controller = controller
    dialog._announce = announced.append
    return dialog, controller, announced


def test_ctrl_down_lowers_recording_playback_volume() -> None:
    dialog, controller, announced = _make_dialog()
    event = _KeyEvent(_WXK_DOWN, ctrl=True)
    dialog._on_char_hook(event)
    assert controller.state.volume_percent == 40
    assert announced == ["Volume 40 percent."]
    assert event.skipped is False


def test_ctrl_up_raises_recording_playback_volume() -> None:
    dialog, controller, announced = _make_dialog()
    dialog._on_char_hook(_KeyEvent(_WXK_UP, ctrl=True))
    assert controller.state.volume_percent == 60
    assert announced == ["Volume 60 percent."]


def test_bare_down_arrow_passes_through_for_row_navigation() -> None:
    dialog, controller, _ = _make_dialog()
    event = _KeyEvent(_WXK_DOWN, ctrl=False)
    dialog._on_char_hook(event)
    assert controller.state.volume_percent == 50
    assert event.skipped is True


def test_ctrl_shift_and_unrelated_ctrl_keys_pass_through() -> None:
    dialog, controller, _ = _make_dialog()
    for event in (
        _KeyEvent(_WXK_DOWN, ctrl=True, shift=True),
        _KeyEvent(_WXK_LEFT, ctrl=True),
    ):
        dialog._on_char_hook(event)
        assert event.skipped is True
    assert controller.state.volume_percent == 50
