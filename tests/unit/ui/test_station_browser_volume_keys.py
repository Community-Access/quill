"""Regression test for issue #1070: Ctrl+Up/Ctrl+Down must change the radio
volume from inside the Browse Stations dialog.

The dialog is modal and its results list claims bare Up/Down for row
navigation, so the frame's Playback-menu Ctrl+Up/Ctrl+Down accelerator never
reaches the volume there. A dialog-wide CHAR_HOOK now handles the Ctrl chord.
These tests drive that handler directly (no live wx.App needed) against fake
controller/widgets, so the key-to-volume wiring is verified headlessly.
"""

from __future__ import annotations

import types

from quill.ui.radio.station_browser_dialog import StationBrowserDialog


class _FakeState:
    def __init__(self) -> None:
        self.volume_percent = 50
        self.muted = False


class _FakeController:
    def __init__(self) -> None:
        self.state = _FakeState()

    def volume_up(self, step: int = 10) -> None:
        self.state.muted = False
        self.state.volume_percent = min(100, self.state.volume_percent + step)

    def volume_down(self, step: int = 10) -> None:
        self.state.muted = False
        self.state.volume_percent = max(0, self.state.volume_percent - step)


class _FakeWidget:
    def __init__(self) -> None:
        self.value: object = None

    def SetValue(self, value: object) -> None:  # noqa: N802 - wx shape
        self.value = value


class _KeyEvent:
    """Minimal stand-in for wx.KeyEvent covering what the handler reads."""

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


# wx key codes the handler compares against (avoids importing wx headlessly).
_WXK_UP = 315
_WXK_DOWN = 317
_WXK_LEFT = 314


def _make_dialog() -> tuple[StationBrowserDialog, _FakeController, list[str]]:
    dialog = StationBrowserDialog.__new__(StationBrowserDialog)
    controller = _FakeController()
    announced: list[str] = []
    dialog._wx = types.SimpleNamespace(WXK_UP=_WXK_UP, WXK_DOWN=_WXK_DOWN)
    dialog._controller = controller
    dialog._volume_slider = _FakeWidget()
    dialog._mute_btn = _FakeWidget()
    dialog._announce = announced.append
    return dialog, controller, announced


def test_ctrl_down_lowers_volume_and_syncs_slider() -> None:
    dialog, controller, announced = _make_dialog()
    event = _KeyEvent(_WXK_DOWN, ctrl=True)

    dialog._on_char_hook(event)

    assert controller.state.volume_percent == 40  # 50 - 10
    assert dialog._volume_slider.value == 40  # dialog slider kept in sync
    assert announced == ["Radio volume 40"]
    assert event.skipped is False  # handled, not passed through


def test_ctrl_up_raises_volume() -> None:
    dialog, controller, announced = _make_dialog()
    dialog._on_char_hook(_KeyEvent(_WXK_UP, ctrl=True))
    assert controller.state.volume_percent == 60
    assert dialog._volume_slider.value == 60
    assert announced == ["Radio volume 60"]


def test_bare_down_arrow_passes_through_to_the_list() -> None:
    # Plain Down (no Ctrl) must reach the results list for row navigation --
    # the handler must not steal it.
    dialog, controller, _ = _make_dialog()
    event = _KeyEvent(_WXK_DOWN, ctrl=False)
    dialog._on_char_hook(event)
    assert controller.state.volume_percent == 50  # unchanged
    assert event.skipped is True


def test_ctrl_shift_down_passes_through() -> None:
    # Ctrl+Shift+Down is not the volume chord; leave it for other handlers.
    dialog, controller, _ = _make_dialog()
    event = _KeyEvent(_WXK_DOWN, ctrl=True, shift=True)
    dialog._on_char_hook(event)
    assert controller.state.volume_percent == 50
    assert event.skipped is True


def test_unrelated_ctrl_key_passes_through() -> None:
    dialog, controller, _ = _make_dialog()
    event = _KeyEvent(_WXK_LEFT, ctrl=True)
    dialog._on_char_hook(event)
    assert controller.state.volume_percent == 50
    assert event.skipped is True
