r"""Enter in Find and Replace runs Find next, which is the one key of that box.

Reported: "I moved to the top, typed frog and pressed Enter, nothing happened.
I had to Tab to the Next button and execute it."

Nothing happened because nothing was listening. ``SetAffirmativeId(wx.ID_OK)``
says which id means yes *when a modal dialog closes*; the Enter key presses the
**default item**, which only ``wxButton::SetDefault`` ever sets. Find is
modeless and never closes on yes, so the affirmative id did nothing here at all
and the box went out with ``GetDefaultItem()`` of ``None``.

Both halves are asserted: the default item exists (so the button looks and
behaves like every other Windows default) and the key is handled outright (so a
modeless dialog is not relying on a plain Enter finding its way out of a text
field, which is a platform detail).
"""

from __future__ import annotations

import pytest
import wx

from quill.apps.lite_find_dialogs import FindDialog, ReplaceDialog


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture()
def frame(wx_app):
    window = wx.Frame(None)
    yield window
    window.Destroy()
    wx_app.Yield()


class _Key:
    """The three things a key handler asks of an event."""

    def __init__(self, code: int, *, shift: bool = False) -> None:
        self._code = code
        self._shift = shift
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802 - wx API shape
        return self._code

    def ShiftDown(self) -> bool:  # noqa: N802 - wx API shape
        return self._shift

    def Skip(self) -> None:  # noqa: N802 - wx API shape
        self.skipped = True


@pytest.fixture()
def find(frame):
    found: list[tuple[str, bool]] = []
    dialog = FindDialog(
        frame, "frog", lambda opts, reverse: found.append((opts["needle"], reverse))
    )
    yield dialog, found
    dialog.Destroy()


def test_enter_finds_the_next_one(find) -> None:
    dialog, found = find
    dialog._on_key(_Key(wx.WXK_RETURN))
    assert found == [("frog", False)]


def test_shift_enter_finds_the_previous_one(find) -> None:
    dialog, found = find
    dialog._on_key(_Key(wx.WXK_RETURN, shift=True))
    assert found == [("frog", True)]


def test_find_next_is_the_dialogs_default_button(find) -> None:
    """What ``SetAffirmativeId`` never did, and what Enter actually presses."""
    dialog, _found = find
    assert dialog.GetDefaultItem() is dialog.next_btn


def test_enter_is_not_left_to_the_platform(find) -> None:
    """A modeless dialog must not depend on Enter escaping a text field."""
    dialog, _found = find
    event = _Key(wx.WXK_RETURN)
    dialog._on_key(event)
    assert event.skipped is False


def test_replace_answers_enter_with_find_next(frame) -> None:
    """Never Replace: the reflex keystroke moves the cursor, it does not edit."""
    found: list[tuple[str, bool]] = []
    replaced: list[object] = []
    dialog = ReplaceDialog(
        frame,
        "frog",
        lambda opts, reverse: found.append((opts["needle"], reverse)),
        lambda opts: replaced.append(opts),
        lambda opts: replaced.append(opts),
    )
    dialog._on_key(_Key(wx.WXK_RETURN))
    assert found == [("frog", False)]
    assert replaced == []
    dialog._on_key(_Key(wx.WXK_RETURN, shift=True))
    assert found[-1] == ("frog", True)
    dialog.Destroy()


def test_replace_enter_works_from_the_replacement_field_too(frame) -> None:
    found: list[tuple[str, bool]] = []
    dialog = ReplaceDialog(
        frame,
        "frog",
        lambda opts, reverse: found.append((opts["needle"], reverse)),
        lambda opts: None,
        lambda opts: None,
    )
    handlers = [field.GetEventHandler() for field in (dialog.text, dialog.replacement)]
    assert all(handler is not None for handler in handlers)
    dialog.replacement.SetValue("toad")
    dialog._on_key(_Key(wx.WXK_RETURN))
    assert found == [("frog", False)]
    dialog.Destroy()
