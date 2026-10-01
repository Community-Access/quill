"""Bare Left and Right belong to the focused control before the transport.

Reported 2026-09-30, from Cast's main window: "left and right say nothing is
playing. Shouldn't those things like arrow keys only move in the player view some
how?"

The bug behind the confusion was worse than the confusion. Bare Left and Right are
mapped to seek-five-seconds, and ``_on_winamp_char_hook`` swallowed them anywhere in
the window except a text field -- which includes the library **tree**, where Left and
Right are collapse and expand. So a keyboard listener could not collapse or expand a
folder or a show in Cast's main surface: the keystroke was eaten and answered
"nothing is playing".

The letters are not affected and must not be, because no letter in the Winamp map
navigates anything -- which is the whole reason the guard is narrow.
"""

from __future__ import annotations

from typing import Any

from quill.ui.podcasts.winamp_mixin import CastWinampKeysMixin


# Each stand-in is its own unrelated class, so ``isinstance`` matches exactly one
# wx name. A shared base made every fake an instance of every name the guard asks
# about -- which quietly turned a button into a combo box and skipped the test.
class _FakeTree:
    pass


class _FakeList:
    pass


class _FakeListBox:
    pass


class _FakeCheckListBox:
    pass


class _FakeText:
    pass


class _FakeCombo:
    pass


class _FakeSearch:
    pass


class _FakeSpin:
    pass


class _FakeChoice:
    pass


class _FakeButton:
    """Focus on something that does not want an arrow for itself."""


class _FakeWindow:
    def __init__(self, focused: Any) -> None:
        self._focused = focused

    def FindFocus(self) -> Any:  # noqa: N802 - wx API shape
        return self._focused


class _FakeWx:
    """Only the names the guard and the key normaliser ask about.

    The WXK_ constants have to be here and have to be the real values: the
    normaliser reads them off the wx module it is handed, so a fake without them
    silently normalises every arrow to "" and the test passes for the wrong reason.
    """

    WXK_LEFT = 314
    WXK_RIGHT = 316
    WXK_UP = 315
    WXK_DOWN = 317

    TreeCtrl = _FakeTree
    ListCtrl = _FakeList
    ListBox = _FakeListBox
    CheckListBox = _FakeCheckListBox
    TextCtrl = _FakeText
    ComboBox = _FakeCombo
    SearchCtrl = _FakeSearch
    SpinCtrl = _FakeSpin
    Choice = _FakeChoice

    def __init__(self, focused: Any) -> None:
        self.Window = _FakeWindow(focused)


class _Host(CastWinampKeysMixin):
    """A Cast-shaped host with nothing but the focus and a record of what ran."""

    def __init__(self, focused: Any) -> None:
        self._wx = _FakeWx(focused)
        self.ran: list[str] = []
        self.skipped = False

    def _run_winamp_action(self, action: str) -> None:
        self.ran.append(action)


class _Event:
    def __init__(self, code: int, **modifiers: bool) -> None:
        self._code = code
        self._modifiers = modifiers
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx API shape
        return self._code

    def ControlDown(self) -> bool:  # noqa: N802 - wx API shape
        return self._modifiers.get("ctrl", False)

    def ShiftDown(self) -> bool:  # noqa: N802 - wx API shape
        return self._modifiers.get("shift", False)

    def AltDown(self) -> bool:  # noqa: N802 - wx API shape
        return self._modifiers.get("alt", False)

    def Skip(self, skip: bool = True) -> None:  # noqa: N802 - wx API shape
        self.skipped = skip


# The real wx codes, so the normaliser under test is the real one.
LEFT = 314
RIGHT = 316
X = ord("X")


def _press(focused: Any, code: int, **modifiers: bool) -> tuple[_Host, _Event]:
    host = _Host(focused)
    event = _Event(code, **modifiers)
    host._on_winamp_char_hook(event)
    return host, event


# -- the bug ------------------------------------------------------------------ #


def test_left_and_right_pass_through_to_a_focused_tree() -> None:
    """In a tree these are collapse and expand. Eating them removed the only
    keyboard route to a whole structure."""
    for code in (LEFT, RIGHT):
        host, event = _press(_FakeTree(), code)
        assert host.ran == [], "the transport swallowed a tree's own navigation key"
        assert event.skipped, "the tree never got the keystroke"


def test_shift_left_and_shift_right_pass_through_to_a_tree_too() -> None:
    """Shift+arrow is back/forward 30 seconds, and is the same mistake."""
    for code in (LEFT, RIGHT):
        host, event = _press(_FakeTree(), code, shift=True)
        assert host.ran == []
        assert event.skipped


def test_left_and_right_pass_through_to_a_focused_list() -> None:
    """A report list uses them to move across columns -- the control's own
    navigation, for the same reason."""
    for code in (LEFT, RIGHT):
        host, _event = _press(_FakeList(), code)
        assert host.ran == []


# -- and the guard stays narrow ----------------------------------------------- #


def test_the_letters_still_work_in_a_tree() -> None:
    """No letter in the Winamp map navigates anything, so the guard must not
    touch them -- otherwise the fix costs the feature."""
    from quill.ui.radio import winamp_keys as wk

    host, _event = _press(_FakeTree(), X)
    assert host.ran == [wk.ACTION_PLAY]


def test_arrows_still_seek_when_focus_is_not_a_navigational_control() -> None:
    """A button, the panel, the status bar: nothing there wants an arrow, so the
    transport keeps them."""
    from quill.ui.radio import winamp_keys as wk

    host, _event = _press(_FakeButton(), LEFT)
    assert host.ran == [wk.ACTION_BACK_5]


def test_a_text_field_still_swallows_nothing_at_all() -> None:
    """The older trap (#1263): a letter binding that eats what is being typed."""
    host, event = _press(_FakeText(), X)
    assert host.ran == []
    assert event.skipped
