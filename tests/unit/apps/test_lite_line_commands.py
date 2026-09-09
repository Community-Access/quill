"""QuillLite's line surgery, and the deletion ring behind Restore Deleted Text.

The mixin is exercised against a stand-in for the wx control rather than a real
one: every command here is a pure text transform plus an announcement, and the
announcement is half of what is being tested. A line move makes no sound of its
own and leaves the caret where it already was, so for a listener the spoken
outcome *is* the feedback -- which means "it did nothing and said nothing" and
"it did nothing and said why" are different results and only one of them is
correct.
"""

from __future__ import annotations

from quill.apps.lite_window_lines import DocumentLineMixin


class _Control:
    """The slice of wx.TextCtrl these commands touch."""

    def __init__(self, text: str, cursor: int = 0) -> None:
        self._text = text
        self._cursor = cursor

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._cursor

    def SetInsertionPoint(self, position: int) -> None:
        self._cursor = position

    def GetLastPosition(self) -> int:
        return len(self._text)

    def Replace(self, start: int, end: int, text: str) -> None:
        self._text = self._text[:start] + text + self._text[end:]


class _Window(DocumentLineMixin):
    def __init__(self, text: str, cursor: int = 0) -> None:
        self.control = _Control(text, cursor)
        self.announcements: list[str] = []
        self.modified = False

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _set_modified(self, value: bool) -> None:
        self.modified = value

    def _touch_status(self) -> None:
        pass


def _window(text: str, cursor: int = 0) -> _Window:
    return _Window(text, cursor)


def test_move_line_up_reorders_and_says_so() -> None:
    win = _window("alpha\nbravo\ncharlie\n", cursor=len("alpha\n") + 1)
    win.cmd_move_line_up()
    assert win.control.GetValue().startswith("bravo\nalpha\n")
    assert win.announcements == ["Moved line up"]
    assert win.modified is True


def test_move_line_up_on_the_first_line_says_why_rather_than_nothing() -> None:
    """Silence and refusal are different answers, and only one is usable."""
    win = _window("alpha\nbravo\n", cursor=0)
    win.cmd_move_line_up()
    assert win.control.GetValue() == "alpha\nbravo\n"
    assert win.announcements == ["Already the first line"]
    assert win.modified is False


def test_move_line_down_reorders() -> None:
    win = _window("alpha\nbravo\ncharlie\n", cursor=0)
    win.cmd_move_line_down()
    assert win.control.GetValue().startswith("bravo\nalpha\n")
    assert win.announcements == ["Moved line down"]


def test_join_lines_pulls_the_next_line_up() -> None:
    win = _window("alpha\nbravo\n", cursor=0)
    win.cmd_join_lines()
    assert win.control.GetValue().startswith("alpha bravo")
    assert win.announcements == ["Joined lines"]


def test_delete_line_announces_what_it_took() -> None:
    """The announcement quotes the line, because it is now the only record."""
    win = _window("alpha\nbravo\ncharlie\n", cursor=len("alpha\n"))
    win.cmd_delete_line()
    assert "bravo" not in win.control.GetValue()
    assert win.announcements == ["Deleted line: bravo"]


def test_restore_deletion_puts_the_text_at_the_cursor_not_where_it_came_from() -> None:
    """The whole point: this is a move, which is what undo cannot give you."""
    win = _window("alpha\nbravo\ncharlie\n", cursor=len("alpha\n"))
    win.cmd_delete_line()
    assert "bravo" not in win.control.GetValue()

    win.control.SetInsertionPoint(win.control.GetLastPosition())
    win.cmd_restore_deletion()

    text = win.control.GetValue()
    assert text.endswith("bravo\n") or text.endswith("bravo")
    assert text.index("charlie") < text.index("bravo")
    assert any("Restored" in message for message in win.announcements)


def test_restore_deletion_with_an_empty_ring_says_so() -> None:
    win = _window("alpha\n", cursor=0)
    win.cmd_restore_deletion()
    assert win.control.GetValue() == "alpha\n"
    assert win.announcements == ["Nothing deleted yet in this document"]


def test_the_ring_is_per_window() -> None:
    """Document 2's deleted paragraph must not be on offer in document 5."""
    first = _window("alpha\nbravo\n", cursor=0)
    first.cmd_delete_line()
    second = _window("charlie\n", cursor=0)

    second.cmd_restore_deletion()

    assert second.announcements == ["Nothing deleted yet in this document"]


def test_moving_a_line_records_nothing_in_the_ring() -> None:
    """A move is not a deletion; offering it back later would be a corruption."""
    win = _window("alpha\nbravo\n", cursor=len("alpha\n"))
    win.cmd_move_line_up()
    assert win._deletion_ring().is_empty()  # noqa: SLF001


def test_delete_to_end_of_line_keeps_the_rest_of_the_document() -> None:
    win = _window("alpha bravo\ncharlie\n", cursor=len("alpha "))
    win.cmd_delete_to_line_end()
    assert win.control.GetValue().startswith("alpha \ncharlie")
    assert any("Deleted to end of line" in message for message in win.announcements)


def test_duplicate_line_does_not_claim_to_have_deleted_anything() -> None:
    win = _window("alpha\n", cursor=0)
    win.cmd_duplicate_line()
    assert win.control.GetValue().count("alpha") == 2
    assert win.announcements == ["Duplicated line"]
