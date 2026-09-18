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

import re
from collections.abc import Callable

import wx

from quill.apps.lite_dialogs import edit_file_format
from quill.apps.lite_dialogs_entry import ask_text
from quill.apps.lite_window_backups import DocumentBackupsMixin
from quill.core import format_ops, line_ops, transforms
from quill.core.lite import APP_NAME
from quill.core.selection import word_span
from quill.core.wrap_ops import hard_wrap
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentToolsMixin"]

#: Below this a wrap width is not a width, it is a column of single letters.
_MIN_WRAP_WIDTH = 20

#: A tool is a function from text to text. QUILL's operations return the new
#: text and nothing else, so the count an announcement needs is worked out here
#: by comparing -- which keeps this the only place that has to know that "how
#: many changed" is a question about the *result*, not about the operation.
_Tool = Callable[[str], str]

#: ``(text, start, end) -> (text, start, end)`` -- the indent helpers' shape.
_IndentOp = Callable[[str, int, int], tuple[str, int, int]]


class DocumentToolsMixin(DocumentBackupsMixin):
    """Line tools, case tools, and the file-format dialog."""

    # ------------------------------------------------------------------ #
    # Running a tool
    # ------------------------------------------------------------------ #

    def _apply_tool(self, tool: _Tool, *, unit: str, verb: str, count: str = "changed") -> None:
        """Run *tool* over the selection, or the whole document if there is none.

        One ``Replace`` rather than a rewrite of the value: it keeps the change
        inside the control's own undo history, so Ctrl+Z takes back the sort as
        one step. Rewriting ``SetValue`` would clear the undo stack and quietly
        cost somebody everything they had typed before it.

        *count* picks which number the announcement carries, and the two are not
        interchangeable. ``"changed"`` -- how much differs -- is right for a tool
        that removes or rewrites: "Removed 2 lines" is the fact. ``"scope"`` -- how
        much the tool was given -- is right for a reordering, where nothing was
        added or taken away and counting the lines that happened to land somewhere
        else understates the work and sends the reader hunting for a line that was
        never missed.
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
        counted = (
            _scope_size(text, unit=unit)
            if count == "scope"
            else _difference(text, changed_text, unit=unit)
        )
        self.control.Replace(start, end, changed_text)
        self.control.SetSelection(start, start + len(changed_text))
        self._set_modified(True)
        self._touch_status()
        plural = "" if counted == 1 else "s"
        self._announce(f"{verb} {counted} {unit}{plural}")

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
        # Counted over the whole scope, not by how many lines ended up somewhere
        # different: a sort of three lines that leaves the middle one where it was
        # is still a sort of three lines, and "Sorted 2 lines" invites the reader
        # to go looking for the one it missed.
        self._apply_tool(format_ops.sort_lines, unit="line", verb="Sorted", count="scope")

    def cmd_sort_lines_descending(self) -> None:
        self._apply_tool(
            lambda text: format_ops.sort_lines(text, descending=True),
            unit="line",
            verb="Sorted",
            count="scope",
        )

    def cmd_remove_blank_lines(self) -> None:
        """Remove every blank line, which is what the menu item says.

        It used to call ``trim_blank_lines``, which removes only the leading and
        trailing ones -- so on any document with blank lines through the middle
        the command removed nothing and then announced "Removed 1 line" for the
        terminal newline it had eaten. Two failures in one keystroke, and the
        second is the worse: a listener cannot see that the text is unchanged and
        has no reason to doubt the sentence.
        """
        self._apply_tool(format_ops.remove_blank_lines, unit="line", verb="Removed")

    def cmd_remove_duplicate_lines(self) -> None:
        self._apply_tool(format_ops.remove_duplicate_lines, unit="line", verb="Removed")

    def cmd_trim_trailing_space(self) -> None:
        self._apply_tool(format_ops.trim_trailing_whitespace, unit="line", verb="Trimmed")

    # ------------------------------------------------------------------ #
    # Case
    # ------------------------------------------------------------------ #

    def _apply_case(self, tool: _Tool) -> None:
        """Change the case of the selection, or of the word the caret is in.

        **The word, not the document.** A line tool with no selection takes the
        whole document, which is the right scope for a sort and the wrong one
        for a case change: Word's ``Shift+F3`` has meant "the word I am on"
        since Word 2.0, and a whole-document UPPERCASE from a chord somebody
        half-pressed is a surprise that costs a Ctrl+Z at best and is not
        noticed at all at worst -- by ear, a document that has changed case is
        a document that reads exactly the same (bad.md N5, 3.4).

        With a selection it is the selection, which is unchanged and is what
        everybody expects.
        """
        start, end = self.control.GetSelection()
        if end > start:
            self._apply_tool(tool, unit="character", verb="Changed")
            return
        text = self.doc_text.text
        word_start, word_end = word_span(text, self.control.GetInsertionPoint())
        word = text[word_start:word_end]
        # ``strip()``, not ``word_end > word_start``: the span helper answers
        # with the run it found, and a caret sitting in three spaces gets three
        # spaces back. Uppercasing those would be a success message for nothing.
        if not word.strip():
            self._announce("Put the cursor in a word, or select some text")
            return
        changed = tool(word)
        if changed == word:
            self._announce(f"{word} is already like that")
            return
        self.control.Replace(word_start, word_end, changed)
        self.control.SetSelection(word_start, word_start + len(changed))
        self._set_modified(True)
        self._touch_status()
        self._announce(f"Changed to {changed}")

    def cmd_upper_case(self) -> None:
        self._apply_case(transforms.to_upper)

    def cmd_lower_case(self) -> None:
        self._apply_case(transforms.to_lower)

    def cmd_title_case(self) -> None:
        self._apply_case(transforms.to_title)

    def cmd_sentence_case(self) -> None:
        """Capital at the start, the rest lowered -- for a heading typed shouting."""
        self._apply_case(transforms.to_sentence_case)

    def cmd_toggle_case(self) -> None:
        """Swap each letter's case, which is the cure for a stuck Caps Lock."""
        self._apply_case(transforms.to_toggle_case)

    # ------------------------------------------------------------------ #
    # More ways to reshape a list of lines
    # ------------------------------------------------------------------ #

    def cmd_reverse_lines(self) -> None:
        self._apply_tool(format_ops.reverse_lines, unit="line", verb="Reversed", count="scope")

    def cmd_normalize_whitespace(self) -> None:
        """Collapse runs of spaces and tabs -- the cure for pasted-in text."""
        self._apply_tool(format_ops.normalize_whitespace, unit="line", verb="Tidied")

    def cmd_quote_lines(self) -> None:
        """Put ``> `` in front of the lines you chose. QUILL's Ctrl+Shift+Q.

        Replying to an email and quoting a log excerpt are Notepad-scale tasks,
        and the engine was already shared: QuillLite had every other line tool
        and not this one (bad.md 4.2, Tier 2).
        """
        self._apply_tool(format_ops.quote_lines, unit="line", verb="Quoted", count="scope")

    def cmd_unquote_lines(self) -> None:
        """Take ``> `` off again."""
        self._apply_tool(format_ops.unquote_lines, unit="line", verb="Unquoted", count="scope")

    def cmd_indentation_to_spaces(self) -> None:
        """Turn the leading tabs of every chosen line into spaces.

        The single most common fix a person makes to somebody else's file, and
        the other half of the concession that QuillLite is where a ``.py`` gets
        opened (bad.md 4.2, Tier 2).
        """
        self._apply_tool(
            format_ops.convert_indentation_to_spaces,
            unit="line",
            verb="Converted",
            count="scope",
        )

    def cmd_indentation_to_tabs(self) -> None:
        """And the other way: leading spaces become tabs."""
        self._apply_tool(
            format_ops.convert_indentation_to_tabs,
            unit="line",
            verb="Converted",
            count="scope",
        )

    def cmd_delete_lines_containing(self) -> None:
        """Delete every chosen line that matches what you type.

        Log triage is exactly why people open a plain-text editor, and doing
        this by hand means reading every line to find the ones to remove --
        which by ear is the whole file, twice (bad.md 4.2, Tier 2).

        A plain search, not a regular expression: QUILL asks for one because
        QUILL's user asked for one, and a ``.`` that silently matches every
        character is a poor surprise in a tool that deletes.
        """
        pattern = ask_text(
            self,
            title="Delete Lines Containing",
            label="Delete every line that &contains:",
            help_text=(
                "Typed exactly, not as a pattern. Only the lines you have "
                "selected are looked at, or the whole document if you have "
                "selected nothing. Control Z takes it back."
            ),
        )
        self.control.SetFocus()
        if pattern is None:
            return
        if not pattern:
            self._announce("Nothing was typed, so no lines were deleted")
            return
        self._apply_tool(
            lambda text: format_ops.delete_lines_containing(text, re.escape(pattern)),
            unit="line",
            verb="Deleted",
            count="changed",
        )

    def cmd_hard_wrap(self) -> None:
        """Re-flow the chosen lines so none is longer than a width you give.

        The *document* changes, which is what makes this different from Word
        Wrap on the View menu: that one changes what you see and is not saved.
        Somebody formatting text to be read on a narrow display, or pasting into
        something that will not wrap for them, needs the real thing.
        """
        answer = ask_text(
            self,
            title="Hard Wrap Lines",
            label="&Longest line, in characters:",
            help_text=(
                "Lines are re-flowed so none is longer than this. Paragraphs "
                "are kept apart; a single word longer than the width is left "
                "whole rather than broken. This changes the document, so it is "
                "saved -- View, Word Wrap is the one that only changes the view."
            ),
            value="72",
        )
        self.control.SetFocus()
        if answer is None:
            return
        try:
            width = int(answer.strip())
        except ValueError:
            self._announce(f"{answer} is not a number of characters")
            return
        if width < _MIN_WRAP_WIDTH:
            self._announce(f"A width of at least {_MIN_WRAP_WIDTH} characters is needed")
            return
        self._apply_tool(
            lambda text: hard_wrap(text, width), unit="line", verb="Wrapped", count="scope"
        )

    def cmd_line_statistics(self) -> None:
        """How long the lines are: the longest, the average, and where it is.

        Document Statistics answers "how big is this"; this answers "how wide",
        which is the question somebody formatting for a braille display or a
        narrow window actually has. Nothing is changed and nothing is selected.
        """
        text = self.doc_text.text
        lines = text.split("\n")
        if not text:
            self._announce("The document is empty")
            return
        widths = [len(line) for line in lines]
        longest = max(widths)
        at = widths.index(longest) + 1
        average = round(sum(widths) / len(widths))
        self._announce(
            f"{len(lines):,} lines. Longest {longest:,} characters, on line {at:,}. "
            f"Average {average:,}."
        )

    def cmd_number_lines(self) -> None:
        self._apply_tool(line_ops.number_lines, unit="line", verb="Numbered")

    # ------------------------------------------------------------------ #
    # Indenting
    # ------------------------------------------------------------------ #

    def _shift_indent(self, shift: _IndentOp, *, verb: str, announce: bool = True) -> None:
        """Indent or outdent the selected lines, or the caret's line.

        Not ``_apply_tool``: indenting is defined by *where the lines are* in
        the document rather than by the text of a selection, and
        :mod:`quill.core.format_ops` already takes and returns offsets for
        exactly that reason. Passing it a slice would indent the selection's
        first line from wherever the selection happened to begin.

        ``announce=False`` is for the Tab key, which says the resulting *depth*
        instead. Two announcements for one keystroke is over-announcing -- the
        second arrives over the first and is the only one heard anyway -- and of
        the two, "4 spaces" carries the information a screen reader does not
        otherwise give. Refusals are still spoken either way: "nothing to
        outdent" is the one outcome where silence and success sound alike.
        """
        text = self.control.GetValue()
        start, end = self.control.GetSelection()
        changed, new_start, new_end = shift(text, start, end)
        if changed == text:
            self._announce("Nothing to outdent")
            return
        self.control.Replace(0, self.control.GetLastPosition(), changed)
        self.control.SetSelection(new_start, new_end)
        self._set_modified(True)
        self._touch_status()
        if not announce:
            return
        lines = max(1, changed[new_start:new_end].count("\n") or 1)
        self._announce(f"{verb} {lines} line{'s' if lines != 1 else ''}")

    def cmd_indent(self, *, announce: bool = True) -> None:
        self._shift_indent(format_ops.indent_lines, verb="Indented", announce=announce)

    def cmd_outdent(self, *, announce: bool = True) -> None:
        self._shift_indent(format_ops.outdent_lines, verb="Outdented", announce=announce)

    def describe_indent_at_cursor(self) -> str:
        """How deeply the caret's line is indented, in words.

        QUILL's own :func:`~quill.core.format_ops.describe_indent_depth`, so
        "4 spaces" means the same thing in both products however it was reached.
        """
        return format_ops.describe_indent_depth(
            self.control.GetValue(), self.control.GetInsertionPoint()
        )

    def cmd_describe_indent(self) -> None:
        """Say the caret line's indentation, on demand.

        The one question about a line that cannot otherwise be asked. A screen
        reader reads a line's *text*; it does not read the spaces or tabs in
        front of it, so in a YAML file, a Python module or a nested list the
        structure of the document is invisible by ear. QuillLite already goes
        quiet about spelling in those files, which is an admission that people
        edit them here -- and for those people this is the fact the editor was
        withholding.

        QUILL had the phrasing and no way to ask for it, only an
        announce-as-you-move toggle that speaks while you are moving and stays
        silent when you stop to wonder. The command was added there first, on
        this same key, because QuillLite may never be ahead of the editor.
        """
        self._announce(self.describe_indent_at_cursor())

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
        # Not in rich text, where the answer would be a lie. A .rtf is written
        # by _write_rtf, which reads neither of these: the dialog dirtied the
        # document, announced "Saving as UTF-16, CRLF" and changed nothing at
        # all, while the status cells went on reading UTF-8 / CRLF for every
        # rich document there is (bad.md F7). A refusal that says why is the
        # honest version of that.
        if self.editor.mode == RICH:
            self._announce(
                "A rich text document has its own format, so the encoding and the "
                "line endings are not yours to choose. They apply to plain text, "
                "Markdown and HTML."
            )
            return
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


# The two counting rules moved into quill/core/line_tool_report.py on
# 2026-09-18 so QUILL could read them too (bad.md P1.16): QUILL's line tools
# announced a past tense and no number at all, including when nothing had
# changed. Same functions, same behaviour, one copy.
from quill.core.line_tool_report import changed_size as _difference  # noqa: E402
from quill.core.line_tool_report import scope_size as _scope_size  # noqa: E402


def _encoding_name(encoding: str) -> str:
    from quill.apps.lite_window_status import encoding_name

    return encoding_name(encoding)


def _newline_name(newline: str) -> str:
    from quill.apps.lite_window_status import newline_name

    return newline_name(newline)
