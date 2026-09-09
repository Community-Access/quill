"""The Tools menu: the things people have to *do* to text, and how it is stored.

Two groups, and both are here for the same reason. Sorting a list of forty
names, lower-casing a heading somebody pasted in shouting, or stripping the
trailing spaces a diff is about to complain about are all jobs that take one
keystroke here and several minutes of arrow keys otherwise -- and "several
minutes of arrow keys" costs a screen-reader user far more than it costs anybody
else.

* **Line and case tools** -- QUILL's own :mod:`quill.core.format_ops` and
  :mod:`quill.core.transforms`, not a second implementation. QuillLite must
  never be *ahead* of QUILL: if a text operation is worth having here it is
  worth having there, and two implementations of "sort these lines" is two
  places for them to start disagreeing about what a trailing newline means.
* **File format** -- the encoding and the line endings this document will be
  written back with. QuillLite already round-trips both faithfully; this is how
  you *change* them on purpose, which is what somebody moving a file between
  Windows and a build server actually needs.

Every tool works on the selection when there is one and on the whole document
when there is not, which is the rule every editor uses and the one nobody has to
be told. Each is a single undoable step: the change goes in through the
control's own ``Replace``, so Ctrl+Z takes back the whole sort rather than
forty separate line moves.

Rich text warning, once and honestly: replacing a run of text in rich mode gives
the new text the formatting of where it lands. The tools that rewrite the whole
document say so before they run.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.apps.lite_dialogs import edit_file_format
from quill.core import format_ops, transforms
from quill.core.lite import APP_NAME
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentToolsMixin"]

#: A tool is a function from text to text. QUILL's operations return the new
#: text and nothing else, so the count an announcement needs is worked out here
#: by comparing -- which keeps this the only place that has to know that "how
#: many changed" is a question about the *result*, not about the operation.
_Tool = Callable[[str], str]


class DocumentToolsMixin:
    """Line tools, case tools, and the file-format dialog."""

    # ------------------------------------------------------------------ #
    # Running a tool
    # ------------------------------------------------------------------ #

    def _apply_tool(self, tool: _Tool, *, unit: str, verb: str) -> None:
        """Run *tool* over the selection, or the whole document if there is none.

        One ``Replace`` rather than a rewrite of the value: it keeps the change
        inside the control's own undo history, so Ctrl+Z takes back the sort as
        one step. Rewriting ``SetValue`` would clear the undo stack and quietly
        cost somebody everything they had typed before it.
        """
        start, end = self.control.GetSelection()
        whole = end <= start
        if whole:
            start, end = 0, self.control.GetLastPosition()
        text = self.control.GetValue()[start:end]
        if not text:
            self._announce("Nothing to change")
            return
        if whole and self.editor.mode == RICH and not self._confirm_rich_rewrite():
            return
        changed_text = tool(text)
        if changed_text == text:
            self._announce(f"No {unit} to change")
            return
        count = _difference(text, changed_text, unit=unit)
        self.control.Replace(start, end, changed_text)
        self.control.SetSelection(start, start + len(changed_text))
        self._set_modified(True)
        self._touch_status()
        plural = "" if count == 1 else "s"
        self._announce(f"{verb} {count} {unit}{plural}")

    def _confirm_rich_rewrite(self) -> bool:
        """Rich mode only: warn that replaced text takes the run's formatting."""
        answer = show_message_box(
            "This rewrites the whole document, and in rich text the replaced "
            "text takes the formatting of where it lands. Continue?",
            APP_NAME,
            # NO_DEFAULT: Enter must not be the key that rewrites the document.
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self,
        )
        return answer == wx.YES

    # ------------------------------------------------------------------ #
    # Lines
    # ------------------------------------------------------------------ #

    def cmd_sort_lines(self) -> None:
        self._apply_tool(format_ops.sort_lines, unit="line", verb="Sorted")

    def cmd_sort_lines_descending(self) -> None:
        self._apply_tool(
            lambda text: format_ops.sort_lines(text, descending=True),
            unit="line",
            verb="Sorted",
        )

    def cmd_remove_blank_lines(self) -> None:
        self._apply_tool(format_ops.trim_blank_lines, unit="line", verb="Removed")

    def cmd_remove_duplicate_lines(self) -> None:
        self._apply_tool(format_ops.remove_duplicate_lines, unit="line", verb="Removed")

    def cmd_trim_trailing_space(self) -> None:
        self._apply_tool(format_ops.trim_trailing_whitespace, unit="line", verb="Trimmed")

    # ------------------------------------------------------------------ #
    # Case
    # ------------------------------------------------------------------ #

    def cmd_upper_case(self) -> None:
        self._apply_tool(transforms.to_upper, unit="character", verb="Changed")

    def cmd_lower_case(self) -> None:
        self._apply_tool(transforms.to_lower, unit="character", verb="Changed")

    def cmd_title_case(self) -> None:
        self._apply_tool(transforms.to_title, unit="character", verb="Changed")

    # ------------------------------------------------------------------ #
    # How the file is written
    # ------------------------------------------------------------------ #

    def cmd_file_format(self) -> None:
        """Choose the encoding and the line endings this document saves with.

        Both are shown in the status bar and both were previously read-only:
        QuillLite wrote back whatever it read, which is the right default and a
        dead end for somebody who needs a UTF-8 copy of a Windows-1252 file, or
        Unix line endings for a build server. Nothing is written here -- the
        choice takes effect at the next save, which is the moment it means
        anything.
        """
        chosen = edit_file_format(self, encoding=self.encoding, newline=self.newline)
        if chosen is None:
            self.control.SetFocus()
            return
        encoding, newline = chosen
        if (encoding, newline) == (self.encoding, self.newline):
            self.control.SetFocus()
            return
        self.encoding, self.newline = encoding, newline
        self._set_modified(True)
        self._touch_status()
        self.control.SetFocus()
        self._announce(f"Saving as {_encoding_name(encoding)}, {_newline_name(newline)}")


def _difference(before: str, after: str, *, unit: str) -> int:
    """How much changed, counted in *unit*, for an announcement that says something.

    Lines when the tool works on lines, characters when it works on characters.
    A count of "1" for a sort of forty lines would be technically true of the
    string and useless to the person who ran it.
    """
    if unit == "line":
        old, new = before.split("\n"), after.split("\n")
        return abs(len(old) - len(new)) or sum(1 for a, b in zip(old, new, strict=False) if a != b)
    if len(before) != len(after):
        return max(len(before), len(after))
    return sum(1 for a, b in zip(before, after, strict=True) if a != b)


def _encoding_name(encoding: str) -> str:
    from quill.apps.lite_window_status import encoding_name

    return encoding_name(encoding)


def _newline_name(newline: str) -> str:
    from quill.apps.lite_window_status import newline_name

    return newline_name(newline)
