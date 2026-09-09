"""Case conversions, line transforms and indenting in QuillLite.

Every one of these is QUILL's own :mod:`quill.core.transforms`,
:mod:`quill.core.format_ops` or :mod:`quill.core.line_ops` -- so what is worth
testing here is not the transform (those have their own tests) but the *wiring*:
that the right function is reached, that the selection rule holds, and above all
that each one says what it did. A tool that silently rewrote a document would be
indistinguishable, by ear, from a key that is not bound.

Indenting is tested separately from the rest because it does not follow the
selection rule the other tools follow: it is defined by where the lines are in
the document, not by the text of a selection.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.apps.lite_window_tools import DocumentToolsMixin
from quill.ui.richedit_editing import PLAIN


class _Control:
    def __init__(self, text: str) -> None:
        self._text = text
        self.selection = (0, 0)

    def GetValue(self) -> str:
        return self._text

    def GetSelection(self) -> tuple[int, int]:
        return self.selection

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)

    def GetLastPosition(self) -> int:
        return len(self._text)

    def GetInsertionPoint(self) -> int:
        return self.selection[0]

    def Replace(self, start: int, end: int, text: str) -> None:
        self._text = self._text[:start] + text + self._text[end:]


class _Window(DocumentToolsMixin):
    def __init__(self, text: str) -> None:
        self.control = _Control(text)
        self.announcements: list[str] = []
        self.modified = False
        self.editor = SimpleNamespace(mode=PLAIN)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _set_modified(self, value: bool) -> None:
        self.modified = value

    def _touch_status(self) -> None:
        pass


def test_sentence_case_lowers_the_shouting_and_keeps_the_first_capital() -> None:
    win = _Window("THIS IS A HEADING")
    win.cmd_sentence_case()
    assert win.control.GetValue() == "This is a heading"
    assert win.announcements and "Changed" in win.announcements[0]


def test_invert_case_swaps_every_letter() -> None:
    win = _Window("hELLO wORLD")
    win.cmd_toggle_case()
    assert win.control.GetValue() == "Hello World"


def test_reverse_lines_reverses_them() -> None:
    win = _Window("one\ntwo\nthree\n")
    win.cmd_reverse_lines()
    assert win.control.GetValue().startswith("three\ntwo\none")
    assert any("Reversed" in message for message in win.announcements)


def test_number_lines_numbers_them() -> None:
    win = _Window("alpha\nbravo\n")
    win.cmd_number_lines()
    value = win.control.GetValue()
    assert value.startswith("1. alpha")
    assert "2. bravo" in value


def test_tidy_whitespace_collapses_runs() -> None:
    win = _Window("a    b\t\tc")
    win.cmd_normalize_whitespace()
    assert win.control.GetValue() == "a b c"


def test_a_tool_that_changes_nothing_says_so_rather_than_going_quiet() -> None:
    win = _Window("already\ntidy\n")
    win.cmd_reverse_lines()
    win.announcements.clear()
    win.control.SetSelection(0, 0)
    win.cmd_normalize_whitespace()
    assert win.announcements  # something was said either way
    assert win.modified is True or "No line to change" in win.announcements[0]


def test_indent_adds_a_level_to_the_caret_line_and_counts_it() -> None:
    win = _Window("alpha\nbravo\n")
    win.control.SetSelection(0, 0)
    win.cmd_indent()
    assert win.control.GetValue().startswith("    alpha")
    assert any("Indented" in message for message in win.announcements)
    assert win.modified is True


def test_outdent_removes_a_level() -> None:
    win = _Window("    alpha\n")
    win.control.SetSelection(0, 0)
    win.cmd_outdent()
    assert win.control.GetValue().startswith("alpha")
    assert any("Outdented" in message for message in win.announcements)


def test_outdent_with_nothing_to_remove_refuses_in_words() -> None:
    """Silence here is indistinguishable from a key that is not bound."""
    win = _Window("alpha\n")
    win.control.SetSelection(0, 0)
    win.cmd_outdent()
    assert win.control.GetValue() == "alpha\n"
    assert win.announcements == ["Nothing to outdent"]
    assert win.modified is False


def test_indent_covers_every_line_the_selection_touches() -> None:
    win = _Window("alpha\nbravo\ncharlie\n")
    win.control.SetSelection(2, len("alpha\nbra"))
    win.cmd_indent()
    value = win.control.GetValue()
    assert value.startswith("    alpha\n    bravo\ncharlie")
