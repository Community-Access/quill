"""Back and Forward: the undo for moving about.

Without it every jump in QuillLite is one-way. Somebody who pressed F3 to check
a word elsewhere in the document, or followed a heading, can only get back to
the paragraph they were writing if they happened to know its line number -- and
the line number is exactly the thing a listener was never told. A reader glances
back; there is no equivalent gesture here, so it has to be a key.

The ring itself is QUILL's (``quill/core/locations.py``) and is tested there.
What is tested here is the wiring, and specifically the two things that make the
difference between a Back key that works and one that appears to:

* every jump records, because they all go through ``_go_to`` -- a jump somebody
  forgot to record is a place Back silently skips;
* Back and Forward do *not* record, or pressing Back twice would bounce between
  the same two positions for ever instead of walking further back.
"""

from __future__ import annotations

from quill.apps.lite_window_commands import DocumentCommandsMixin
from quill.apps.lite_window_history import DocumentHistoryMixin
from quill.core.locations import LocationRing


class _Control:
    def __init__(self, text: str) -> None:
        self._text = text
        self._cursor = 0
        self.shown = -1

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._cursor

    def SetInsertionPoint(self, position: int) -> None:
        self._cursor = position

    def ShowPosition(self, position: int) -> None:
        self.shown = position

    def SetFocus(self) -> None:
        pass

    def GetLastPosition(self) -> int:
        return len(self._text)


class _Window(DocumentCommandsMixin, DocumentHistoryMixin):
    def __init__(self, text: str = "x" * 400) -> None:
        self.control = _Control(text)
        self.locations = LocationRing()
        self.announcements: list[str] = []

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _touch_status(self) -> None:
        pass


def test_back_returns_to_where_the_jump_started() -> None:
    win = _Window()
    win.control.SetInsertionPoint(10)

    win._go_to(200)
    assert win.control.GetInsertionPoint() == 200

    win.cmd_back_location()

    assert win.control.GetInsertionPoint() == 10
    assert win.announcements == ["Went back"]


def test_back_walks_further_back_rather_than_bouncing() -> None:
    """The bug a naive implementation ships: Back that records its own move.

    If Back pushed the place it just left onto the ring, the second press would
    return to the first -- and Back would toggle between two positions for ever
    while appearing to work.
    """
    win = _Window()
    win.control.SetInsertionPoint(10)
    win._go_to(100)
    win._go_to(300)

    win.cmd_back_location()
    win.cmd_back_location()

    assert win.control.GetInsertionPoint() == 10


def test_forward_undoes_a_back() -> None:
    win = _Window()
    win.control.SetInsertionPoint(10)
    win._go_to(250)
    win.cmd_back_location()

    win.cmd_forward_location()

    assert win.control.GetInsertionPoint() == 250
    assert win.announcements[-1] == "Went forward"


def test_with_nowhere_to_go_it_says_so_rather_than_going_quiet() -> None:
    """Silence is indistinguishable by ear from a key that is not bound."""
    win = _Window()

    win.cmd_back_location()
    assert win.announcements == ["No earlier place"]

    win.cmd_forward_location()
    assert win.announcements[-1] == "No later place"


def test_a_remembered_place_past_the_end_lands_inside_the_document() -> None:
    """The document can have been shortened since the jump was recorded."""
    win = _Window("short")
    win.locations.record(4000)
    win.locations.record(0)

    win.cmd_back_location()

    assert win.control.GetInsertionPoint() == len("short")


def test_the_caret_is_scrolled_to_and_not_merely_moved() -> None:
    """A caret the window has not scrolled to is one a magnifier user cannot see."""
    win = _Window()
    win.control.SetInsertionPoint(5)
    win._go_to(300)

    win.cmd_back_location()

    assert win.control.shown == 5
