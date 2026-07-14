"""Keyboard preview activation in the voice browser dialog (issue #709).

A wx.ListBox emits no item-activated event, so Enter and Space must be handled
explicitly to match the double-click preview. ``_on_voice_key_down`` depends only
on the injected ``self._wx`` constants and ``self._do_preview``, so it is tested
here with light stubs (no real wxPython display required).
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.read_aloud import (  # noqa: F401  (import proves the module loads)
    discover_dectalk_executable,
)
from quill.ui.voice_browser_dialog import VoiceBrowserDialog

# Distinct sentinel key codes; only equality with self._wx matters.
_WX = SimpleNamespace(WXK_RETURN=13, WXK_NUMPAD_ENTER=370, WXK_SPACE=32)


class _Event:
    def __init__(self, key: int) -> None:
        self._key = key
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._key

    def Skip(self) -> None:
        self.skipped = True


def _press(key: int) -> tuple[bool, bool]:
    """Return (previewed, skipped) after dispatching *key* to the handler."""
    calls: list[int] = []
    stub = SimpleNamespace(_wx=_WX, _do_preview=lambda: calls.append(1))
    event = _Event(key)
    VoiceBrowserDialog._on_voice_key_down(stub, event)
    return bool(calls), event.skipped


def test_enter_previews() -> None:
    previewed, skipped = _press(_WX.WXK_RETURN)
    assert previewed is True
    assert skipped is False  # event consumed so the default button doesn't also fire


def test_numpad_enter_previews() -> None:
    previewed, skipped = _press(_WX.WXK_NUMPAD_ENTER)
    assert previewed is True
    assert skipped is False


def test_space_previews() -> None:
    # The #709 regression: Space did nothing before.
    previewed, skipped = _press(_WX.WXK_SPACE)
    assert previewed is True
    assert skipped is False


def test_other_keys_skip() -> None:
    previewed, skipped = _press(65)  # 'A'
    assert previewed is False
    assert skipped is True  # let arrow/letter navigation through
