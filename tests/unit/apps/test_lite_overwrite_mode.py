"""QUILL Lite's Typing Mode cell has to be true, or it is worse than absent.

The native control implements insert-versus-overwrite itself, toggles it on
VK_INSERT, and will not report which mode it is in. So QUILL Lite mirrors the
mode, and the only thing that makes the mirror trustworthy is that *every* route
which changes the control also moves the mirror -- the command, and the Insert
key the control answers whether QUILL Lite asks it to or not.

QUILL shipped the other version of this: a flag the status bar rendered and
nothing else ever changed, so the cell could read "Overwrite" while typing still
inserted. That is the failure these tests exist to keep out of the small
product, and it is the reason the command refuses instead of announcing when the
control cannot be told.
"""

from __future__ import annotations

import wx

from quill.apps.lite_window_menus import DocumentMenuMixin
from quill.apps.lite_window_status import CELLS
from quill.apps.lite_window_typing import DocumentTypingMixin
from quill.ui.extend_selection_mode import ExtendSelectionMixin


class _RichEdit:
    """The one method the command uses, plus a record of the calls."""

    def __init__(self, *, works: bool = True) -> None:
        self.works = works
        self.calls = 0

    def toggle_overtype(self) -> bool:
        self.calls += 1
        return self.works


class _Window(ExtendSelectionMixin, DocumentTypingMixin):
    """The typing mixin, with the shared Extend Selection Mode beside it.

    The real one rather than a stand-in: the key hook offers every navigation
    key to the mode before the control sees it, so a stub without it fails on
    an AttributeError in the middle of an overwrite test and tells you nothing
    about overwrite.
    """

    def __init__(self, *, works: bool = True) -> None:
        self.editor = _RichEdit(works=works)
        self.announcements: list[str] = []
        self.touched = 0
        self.synced = 0
        self.guard_during_toggle: list[bool] = []
        self._init_overwrite()

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _touch_status(self) -> None:
        self.touched += 1

    def _sync_check_items(self) -> None:
        self.synced += 1

    def sound_is_quiet(self) -> bool:
        """Read by _sync_check_items for the Quiet Mode mark."""
        return False


class _KeyEvent:
    def __init__(self, code: int) -> None:
        self._code = code
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._code

    def Skip(self) -> None:
        self.skipped = True


def test_the_command_tells_the_control_and_then_moves_the_mirror() -> None:
    win = _Window()

    win.cmd_toggle_overwrite()

    assert win.editor.calls == 1
    assert win._overwrite_mode is True
    assert win.announcements == ["Overwrite mode on"]

    win.cmd_toggle_overwrite()

    assert win.editor.calls == 2
    assert win._overwrite_mode is False
    assert win.announcements[-1] == "Insert mode on"


def test_the_command_refuses_rather_than_claiming_a_mode_it_could_not_set() -> None:
    win = _Window(works=False)

    win.cmd_toggle_overwrite()

    assert win._overwrite_mode is False
    assert win.announcements == ["Overwrite mode is not available on this editing surface"]


def test_the_insert_key_is_watched_and_never_swallowed() -> None:
    """The control does the overtype; all QUILL Lite adds is that the cell knows.

    ``Skip`` is load-bearing twice over: it is what lets the control act at all,
    and Insert is NVDA's and JAWS's modifier, so a handler that consumed it
    would be taking a key out of the screen reader's hands.
    """
    win = _Window()
    event = _KeyEvent(wx.WXK_INSERT)

    win._on_key_down(event)

    assert event.skipped is True
    assert win._overwrite_mode is True
    assert win.touched == 1

    win._on_key_down(_KeyEvent(wx.WXK_INSERT))

    assert win._overwrite_mode is False


def test_the_synthesised_insert_is_not_mistaken_for_the_user_pressing_it() -> None:
    """The command's own keystroke reaches this handler; it must change nothing.

    Without the guard the mirror would move twice per command and end up
    reporting the opposite of the truth.
    """
    win = _Window()
    win._overwrite_mode = True
    win._synthetic_insert_key = True
    event = _KeyEvent(wx.WXK_INSERT)

    win._on_key_down(event)

    assert win._overwrite_mode is True
    assert event.skipped is True


def test_an_ordinary_key_leaves_the_mirror_alone() -> None:
    win = _Window()

    win._on_key_down(_KeyEvent(ord("A")))

    assert win._overwrite_mode is False
    assert win.touched == 0


def test_the_menu_mark_reads_the_same_flag_the_cell_does() -> None:
    """Two readouts of one mode that could disagree would be two bugs, not one."""
    win = _Window()
    win._overwrite_mode = True

    class _Item:
        def __init__(self) -> None:
            self.checked: bool | None = None

        def Check(self, value: bool) -> None:
            self.checked = value

    item = _Item()
    win._check_items = {"cmd_toggle_overwrite": item}
    settings = type(
        "Settings", (), {"theme": "system", "word_wrap": True, "show_status_bar": True}
    )()
    win.app = type(
        "App", (), {"settings": settings, "feature_enabled": staticmethod(lambda _area: True)}
    )()
    DocumentMenuMixin._sync_check_items(win)

    assert item.checked is True


def test_the_typing_mode_cell_is_on_the_bar_and_acts_on_enter() -> None:
    """A cell that only reads is half the feature: Enter has to switch it too."""
    from quill.apps.lite_window_status import _CELL_ACTIONS

    keys = [cell.key for cell in CELLS]
    assert "typing_mode" in keys
    assert _CELL_ACTIONS["typing_mode"] == "cmd_toggle_overwrite"


# --------------------------------------------------------------------------- #
# Tab mode, and the depth nothing else will tell you
# --------------------------------------------------------------------------- #


class _TabControl:
    """The slice of the control the indent path touches."""

    def __init__(self, text: str, cursor: int) -> None:
        self._text = text
        self._cursor = cursor

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._cursor


class _TabWindow(_Window):
    def __init__(self, text: str = "    hello", cursor: int = 6) -> None:
        super().__init__()
        self.control = _TabControl(text, cursor)
        self.indented = 0
        self.outdented = 0
        #: What each indent call was asked to announce. Tab says the resulting
        #: depth itself, so the indent underneath it must stay quiet: two
        #: announcements for one keystroke is over-announcing, and the second
        #: arrives over the first.
        self.announce_asked: list[bool] = []

    def cmd_indent(self, *, announce: bool = True) -> None:
        self.indented += 1
        self.announce_asked.append(announce)

    def cmd_outdent(self, *, announce: bool = True) -> None:
        self.outdented += 1
        self.announce_asked.append(announce)

    def describe_indent_at_cursor(self) -> str:
        return "4 spaces"

    def markup_surface(self) -> str | None:
        """What kind of document this is, which is what decides Tab's meaning
        until somebody uses the toggle (bad.md T3, P1.21). None is a plain
        document, where Tab types a tab."""
        return None


class _ShiftKeyEvent(_KeyEvent):
    def __init__(self, code: int, *, shift: bool = False) -> None:
        super().__init__(code)
        self._shift = shift

    def ShiftDown(self) -> bool:
        return self._shift


def test_quilllite_starts_where_notepad_does_and_lets_tab_through() -> None:
    """The default must not change what Tab already did for existing users."""
    win = _TabWindow()
    assert win._tab_inserts_literal is True
    event = _ShiftKeyEvent(wx.WXK_TAB)

    win._on_key_down(event)

    assert win.indented == 0
    # Skipped, so the control -- built with TE_PROCESS_TAB -- types the tab.
    assert event.skipped is True


def test_with_the_toggle_cleared_tab_indents_and_speaks_the_new_depth() -> None:
    """ "Indented 1 line" is not the answer; the depth is, because nothing reads it."""
    win = _TabWindow()
    win.cmd_toggle_tab_mode()
    win.announcements.clear()  # the toggle's own announcement, not Tab's
    event = _ShiftKeyEvent(wx.WXK_TAB)

    win._on_key_down(event)

    assert win.indented == 1
    assert event.skipped is False, "the control must not also type a tab"
    assert win.announcements == ["4 spaces"], "one keystroke, one announcement"
    assert win.announce_asked == [False], "the indent itself must not also speak"


def test_shift_tab_outdents_in_either_mode() -> None:
    """A tab typed by accident is undone with one key, whichever mode you are in."""
    win = _TabWindow()
    assert win._tab_inserts_literal is True

    win._on_key_down(_ShiftKeyEvent(wx.WXK_TAB, shift=True))

    assert win.outdented == 1
    assert win.announcements[-1] == "4 spaces"

    win.cmd_toggle_tab_mode()
    win._on_key_down(_ShiftKeyEvent(wx.WXK_TAB, shift=True))

    assert win.outdented == 2


def test_toggling_tab_mode_says_which_way_it_went() -> None:
    """The first press flips away from whatever the document kind was saying.

    A plain document types a tab (bad.md T3), so the first toggle indents.
    """
    win = _TabWindow()

    win.cmd_toggle_tab_mode()
    assert win._tab_inserts_literal is False
    assert win.announcements[-1] == "Tab key indents the line"

    win.cmd_toggle_tab_mode()
    assert win._tab_inserts_literal is True
    assert win.announcements[-1] == "Tab key types a tab character"
