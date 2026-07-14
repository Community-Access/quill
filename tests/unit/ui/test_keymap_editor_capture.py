"""The Record Keys event->binding conversion, exercised without a real wx app."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.keymap_editor import KeymapEditorMixin
from quill.ui.main_frame_quill_key import QuillKeyMixin

_FAKE_WX = SimpleNamespace(
    WXK_RETURN=13,
    WXK_TAB=9,
    WXK_SPACE=32,
    WXK_ESCAPE=27,
    WXK_DELETE=127,
    WXK_BACK=8,
    WXK_HOME=313,
    WXK_END=312,
    WXK_LEFT=314,
    WXK_RIGHT=316,
    WXK_UP=315,
    WXK_DOWN=317,
    WXK_SHIFT=306,
    WXK_ALT=307,
    WXK_CONTROL=308,
    WXK_RAW_CONTROL=309,
    WXK_WINDOWS_LEFT=393,
    WXK_WINDOWS_RIGHT=394,
    **{f"WXK_F{i}": 339 + i for i in range(1, 13)},
)


class _Stub(KeymapEditorMixin, QuillKeyMixin):
    def __init__(self) -> None:
        self._wx = _FAKE_WX


class _Event:
    def __init__(self, code: int, *, ctrl: bool = False, alt: bool = False, shift: bool = False):
        self._code = code
        self._ctrl = ctrl
        self._alt = alt
        self._shift = shift

    def GetKeyCode(self) -> int:
        return self._code

    def ControlDown(self) -> bool:
        return self._ctrl

    def AltDown(self) -> bool:
        return self._alt

    def ShiftDown(self) -> bool:
        return self._shift


def test_letter_with_modifiers() -> None:
    stub = _Stub()
    assert stub._event_to_binding_string(_Event(ord("K"), ctrl=True, shift=True)) == "Ctrl+Shift+K"


def test_modifier_order_is_ctrl_alt_shift() -> None:
    stub = _Stub()
    got = stub._event_to_binding_string(_Event(ord("M"), ctrl=True, alt=True, shift=True))
    assert got == "Ctrl+Alt+Shift+M"


def test_bare_modifier_returns_none() -> None:
    stub = _Stub()
    assert stub._event_to_binding_string(_Event(_FAKE_WX.WXK_CONTROL, ctrl=True)) is None
    assert stub._event_to_binding_string(_Event(_FAKE_WX.WXK_SHIFT, shift=True)) is None


def test_function_and_named_keys() -> None:
    stub = _Stub()
    assert stub._event_to_binding_string(_Event(_FAKE_WX.WXK_F2)) == "F2"
    assert stub._event_to_binding_string(_Event(_FAKE_WX.WXK_UP, ctrl=True)) == "Ctrl+Up"
    assert stub._event_to_binding_string(_Event(_FAKE_WX.WXK_RETURN, alt=True)) == "Alt+Enter"


def test_plain_letter_uppercased() -> None:
    stub = _Stub()
    assert stub._event_to_binding_string(_Event(ord("a"))) == "A"
