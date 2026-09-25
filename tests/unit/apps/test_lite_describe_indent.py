"""Describe Indent Depth: the one fact about a line that nothing else reads out.

A screen reader reads a line's words and not the whitespace in front of them, so
the shape of a YAML file, a Python module or a nested list is invisible by ear.
QUILL held the phrasing for this since ``format_ops.describe_indent_depth`` was
written and never bound a command to it -- only an announce-as-you-move toggle,
which speaks while you are moving and goes quiet at the moment you stop and
wonder. Both products now answer on demand, on one key.

The transform itself is tested in ``tests/unit/core``; what is tested here is
that QUILL Lite reaches it, over the real control's offsets, and *says* the
answer -- an informational command that computes the right string and announces
nothing has done nothing at all.
"""

from __future__ import annotations

from quill.apps.lite_window_tools import DocumentToolsMixin


class _Control:
    def __init__(self, text: str, cursor: int) -> None:
        self._text = text
        self._cursor = cursor

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._cursor


class _Window(DocumentToolsMixin):
    def __init__(self, text: str, cursor: int) -> None:
        self.control = _Control(text, cursor)
        self.announcements: list[str] = []

    def _announce(self, message: str) -> None:
        self.announcements.append(message)


def _window(text: str, cursor: int) -> _Window:
    return _Window(text, cursor)


def test_spaces_are_counted_from_the_line_the_cursor_is_on() -> None:
    win = _window("no indent\n    four spaces\n", cursor=len("no indent\n") + 6)

    win.cmd_describe_indent()

    assert win.announcements == ["4 spaces"]


def test_a_tab_and_a_space_are_told_apart() -> None:
    """The failure this command exists for: two lines that read identically.

    A line indented with a tab and a line indented with spaces are the same
    line to a listener, and in a Python file only one of them runs.
    """
    win = _window("\t   tabbed", cursor=5)

    win.cmd_describe_indent()

    assert win.announcements == ["1 tab, 3 spaces"]


def test_an_unindented_line_says_so_rather_than_going_quiet() -> None:
    """Silence would be indistinguishable from a key that is not bound."""
    win = _window("flush left", cursor=3)

    win.cmd_describe_indent()

    assert win.announcements == ["No indentation"]


def test_the_helper_and_the_command_agree() -> None:
    """Tab announces through the helper and the command announces through it too."""
    win = _window("        deep", cursor=9)

    assert win.describe_indent_at_cursor() == "8 spaces"
    win.cmd_describe_indent()
    assert win.announcements == ["8 spaces"]
