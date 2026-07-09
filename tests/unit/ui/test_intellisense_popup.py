"""The word-prediction popup must never trap keyboard / screen-reader focus.

The intended flow keeps focus in the editor and drives the suggestion list from
the editor's char hook, but focus can still land in the floating listbox (Tab,
mouse, or a screen reader navigating into the window). A bare wx.ListBox has no
way out, so the popup binds its own key handler. These tests exercise that
handler in isolation (no wx app needed)."""

from __future__ import annotations

import types

from quill.ui.main_frame import _IntellisensePopup


class _Event:
    def __init__(self, key_code: int) -> None:
        self._key_code = key_code
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._key_code

    def Skip(self) -> None:
        self.skipped = True


# Minimal stand-in for the wx key constants the handler reads.
_WX = types.SimpleNamespace(
    WXK_ESCAPE=27,
    WXK_RETURN=13,
    WXK_NUMPAD_ENTER=370,
    WXK_TAB=9,
    WXK_UP=315,
    WXK_DOWN=317,
)


def _make_popup() -> tuple[_IntellisensePopup, list[str]]:
    popup = _IntellisensePopup.__new__(_IntellisensePopup)
    popup._wx = _WX
    calls: list[str] = []
    popup.set_accept_callback(lambda: calls.append("accept"))
    popup.set_dismiss_callback(lambda: calls.append("dismiss"))
    return popup, calls


def test_escape_dismisses_popup() -> None:
    popup, calls = _make_popup()
    event = _Event(_WX.WXK_ESCAPE)
    popup._on_listbox_key(event)
    assert calls == ["dismiss"]
    assert event.skipped is False


def test_enter_accepts_selection() -> None:
    popup, calls = _make_popup()
    event = _Event(_WX.WXK_RETURN)
    popup._on_listbox_key(event)
    assert calls == ["accept"]
    assert event.skipped is False


def test_tab_accepts_and_leaves_the_list() -> None:
    popup, calls = _make_popup()
    event = _Event(_WX.WXK_TAB)
    popup._on_listbox_key(event)
    # Tab must not fall through to native list navigation that would strand the
    # user; it accepts and returns focus to the editor.
    assert calls == ["accept"]
    assert event.skipped is False


def test_arrow_keys_fall_through_to_native_list() -> None:
    popup, calls = _make_popup()
    for key in (_WX.WXK_UP, _WX.WXK_DOWN):
        event = _Event(key)
        popup._on_listbox_key(event)
        assert event.skipped is True
    assert calls == []


def test_tab_without_accept_callback_falls_back_to_dismiss() -> None:
    popup, calls = _make_popup()
    popup.set_accept_callback(None)
    event = _Event(_WX.WXK_TAB)
    popup._on_listbox_key(event)
    assert calls == ["dismiss"]


class _DeletedFrame:
    """Stands in for a wx.Frame whose C/C++ side has already been destroyed."""

    def IsShown(self) -> bool:
        raise RuntimeError("wrapped C/C++ object of type Frame has been deleted")


def test_is_visible_survives_a_deleted_frame() -> None:
    """Regression for #917/#918: a stale popup reference (e.g. surviving a
    crash-recovery restart that tore down and rebuilt the parent frame) must
    report "not visible" instead of propagating RuntimeError -- that
    RuntimeError, uncaught, is exactly what crashed _handle_intellisense_key_down."""
    popup, _calls = _make_popup()
    popup.frame = _DeletedFrame()
    assert popup.is_visible() is False
