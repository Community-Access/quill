"""Every command a QuillLite document window can run.

One mixin rather than a second window class: :class:`DocumentFrame` is the
window -- its menus, its state, its file I/O -- and this is what its menu items
*do*. They are separated because a window that builds itself and answers fifty
commands is a module nobody can read, and because the split lets each half stay
inside the repository's module-size budget (GATE-11) without either becoming a
grab bag.

Two rules run through all of them:

* **Say the outcome, and only the outcome.** Every handler that changes
  something announces what changed ("Bold on", "Saved notes.txt", "Replaced 4
  occurrences"). None of them announces a window title, a focus move, a control
  name or a selection -- the screen reader says those already, and saying them
  twice is the over-announcing GATE-13 exists to catch.
* **Refuse in words, not in silence.** A formatting command in plain text says
  so, and says which key switches modes. A command that quietly does nothing is
  indistinguishable, to a listener, from a key that is not bound.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import wx

from quill.apps.lite_dialogs import (
    ask_line_number,
    choose_heading,
    show_text_window,
)
from quill.apps.lite_find_dialogs import (
    FindDialog,
    ReplaceDialog,
    choose_match,
)
from quill.core.find_model import (
    CompiledQuery,
    FindModelError,
    FindQuery,
    all_matches,
    compile_query,
    context_sentence,
    count_matches,
    find_next,
)
from quill.core.lite import APP_NAME, APP_VERSION
from quill.core.lite.commands import shortcut_text
from quill.core.lite.filetypes import (
    OPEN_WILDCARD,
    SAVE_WILDCARD_PLAIN,
    SAVE_WILDCARD_RICH,
    is_rich_path,
)
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import (
    PLAIN,
    RICH,
)

__all__ = ["DocumentCommandsMixin"]

#: Date and time, in the order most of the English-speaking world writes it.
_DATETIME_FORMAT = "%H:%M %d/%m/%Y"


class DocumentCommandsMixin:
    """The ``cmd_*`` handlers the command table names.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``control``, ``editor``, ``app``, ``path``, ``_announce`` and the document
    state these read and change.
    """

    # ------------------------------------------------------------------ #
    # File
    # ------------------------------------------------------------------ #

    def cmd_new(self) -> None:
        self.app.new_window(self.app.settings.default_mode)

    def cmd_new_rich(self) -> None:
        self.app.new_window(RICH)

    def cmd_new_plain(self) -> None:
        self.app.new_window(PLAIN)

    def cmd_open(self) -> None:
        """Open one or more files. A blank window is reused rather than orphaned."""
        with wx.FileDialog(
            self,
            "Open",
            defaultDir=str(self.path.parent) if self.path else "",
            wildcard=OPEN_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            paths = [Path(chosen) for chosen in dialog.GetPaths()]
        for index, path in enumerate(paths):
            # Only the first file may claim this window, and only if it is
            # empty: opening four files must not silently discard the first
            # three windows' worth of work.
            reuse = self if index == 0 and self._is_blank() else None
            self.app.open_path(path, reuse=reuse)

    def _is_blank(self) -> bool:
        return self.path is None and not self.modified and not self.control.GetValue()

    def cmd_save(self) -> None:
        self.save()

    def cmd_save_as(self) -> bool:
        """Ask for a name, converting the document if the extension asks for it."""
        rich = self.editor.mode == RICH
        default_name = self.path.name if self.path else ("Untitled.rtf" if rich else "Untitled.txt")
        with wx.FileDialog(
            self,
            "Save As",
            defaultDir=str(self.path.parent) if self.path else "",
            defaultFile=default_name,
            wildcard=SAVE_WILDCARD_RICH if rich else SAVE_WILDCARD_PLAIN,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return False
            target = Path(dialog.GetPath())
        wants_rich = is_rich_path(target.name)
        if wants_rich and not rich:
            self.switch_mode(RICH)
        elif not wants_rich and rich and not self._confirm_flatten_to_plain():
            return False
        return self.save(target)

    def _confirm_flatten_to_plain(self) -> bool:
        """Warn before a Save As that throws the formatting away, then do it."""
        answer = show_message_box(
            "Saving as plain text removes all formatting. Continue?",
            APP_NAME,
            # NO_DEFAULT because this loses formatting: a listener pressing Enter
            # reflexively must not be the one who throws it away.
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self,
        )
        if answer != wx.YES:
            return False
        text = self.control.GetValue()
        self._loading = True
        try:
            self._set_mode_internal(PLAIN)
            self.control.ChangeValue(text)
            self.apply_theme()
        finally:
            self._loading = False
        return True

    def cmd_close(self) -> None:
        self.Close()

    def cmd_exit(self) -> None:
        self.app.exit_all()

    # ------------------------------------------------------------------ #
    # Edit
    # ------------------------------------------------------------------ #

    def cmd_undo(self) -> None:
        if self.control.CanUndo():
            self.control.Undo()
        else:
            self._announce("Nothing to undo")

    def cmd_redo(self) -> None:
        if self.control.CanRedo():
            self.control.Redo()
        else:
            self._announce("Nothing to redo")

    def cmd_cut(self) -> None:
        self.control.Cut()

    def cmd_copy(self) -> None:
        self.control.Copy()

    def cmd_paste(self) -> None:
        self.control.Paste()

    def cmd_delete(self) -> None:
        """Notepad's Edit > Delete: remove the selection, or the next character.

        The Del key already does this inside the control. The menu item exists
        because a menu is how somebody finds out that it does, and because
        Notepad has had the item since 1985.
        """
        start, end = self.control.GetSelection()
        if end > start:
            self.control.Remove(start, end)
        else:
            self.control.Remove(start, min(start + 1, self.control.GetLastPosition()))

    def cmd_select_all(self) -> None:
        self.control.SelectAll()

    def cmd_insert_datetime(self) -> None:
        self.control.WriteText(time.strftime(_DATETIME_FORMAT))

    def cmd_goto_line(self) -> None:
        total = max(1, self.control.GetNumberOfLines())
        _ok, _column, line = self.control.PositionToXY(self.control.GetInsertionPoint())
        chosen = ask_line_number(self, line + 1, total)
        if chosen is None:
            self.control.SetFocus()
            return
        position = self.control.XYToPosition(0, chosen - 1)
        if position < 0:
            position = self.control.GetLastPosition()
        self._go_to(position)

    def go_to_line_number(self, line: int) -> None:
        """Put the caret at the start of *line* (1-based). Clamped, never refused.

        Public because it is the callback Go To Anything uses to land on a
        heading, and because "go to a line" is a reasonable thing for anything
        else to ask a document window for.
        """
        position = self.control.XYToPosition(0, max(0, int(line) - 1))
        self._go_to(position if position >= 0 else self.control.GetLastPosition())

    def _go_to(self, position: int) -> None:
        """Put the caret at *position*, scroll it into view, and take focus back.

        Nothing is announced: the caret move is a focus/selection change, which
        the screen reader reads out of the control itself.

        Every jump in QuillLite comes through here -- Go To Line, Go To
        Anything, the heading commands, the heading list, the bookmarks -- which
        is why this is where the location ring is fed. One seam rather than a
        ``record`` call beside each caller, because the failure mode of the
        second arrangement is a jump somebody forgot to record, and a Back key
        that skips one of the places you have been is worse than no Back key.
        """
        self._record_location()
        self.control.SetInsertionPoint(position)
        self.control.ShowPosition(position)
        self.control.SetFocus()
        self._touch_status()

    # -- find and replace ------------------------------------------------ #

    def _selected_or_last_needle(self) -> str:
        """What Find should open with: the selection, else the last search."""
        start, end = self.control.GetSelection()
        if end > start:
            return str(self.control.GetValue()[start:end])
        return str(self._find_options.get("needle", ""))

    def cmd_find(self) -> None:
        if self._find_dialog is not None:
            try:
                self._find_dialog.Raise()
                return
            except RuntimeError:  # the wx object is gone; build a fresh one
                self._find_dialog = None
        self._find_dialog = FindDialog(
            self,
            self._selected_or_last_needle(),
            self._do_find,
            self.peek_match_count,
        )
        self._find_dialog.Bind(wx.EVT_WINDOW_DESTROY, self._forget_find_dialog)
        self._find_dialog.Show()

    def _forget_find_dialog(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self._find_dialog:
            self._find_dialog = None
        event.Skip()

    def cmd_find_next(self) -> None:
        self._repeat_find(reverse=False)

    def cmd_find_previous(self) -> None:
        self._repeat_find(reverse=True)

    def _repeat_find(self, *, reverse: bool) -> None:
        if not self._find_options.get("needle"):
            self.cmd_find()
            return
        self._do_find(self._find_options, reverse)

    def _query(self, options: dict[str, Any]) -> CompiledQuery | None:
        """The compiled search, or ``None`` when there is nothing to look for.

        QUILL's own :mod:`quill.core.find_model`, not a private regex: it is
        what carries the three search modes, the 1-based line and column a
        match is announced with, and the counting the peek and Count
        Occurrences both read. A second implementation here would be a second
        place for "what counts as a match" to drift.

        A malformed regular expression is *reported*, not swallowed. A search
        that found nothing and a search that could not run are different facts,
        and only one of them is fixed by retyping the pattern.
        """
        needle = str(options.get("needle", ""))
        if not needle:
            return None
        query = FindQuery(
            text=needle,
            mode=str(options.get("mode", "normal")),  # type: ignore[arg-type]
            case_sensitive=bool(options.get("match_case")),
            whole_word=bool(options.get("whole_word")),
        )
        try:
            return compile_query(query)
        except FindModelError as error:
            self._announce(str(error))
            return None

    def _do_find(self, options: dict[str, Any], reverse: bool) -> bool:
        """Find and select the next (or previous) match, wrapping and saying so."""
        compiled = self._query(options)
        if compiled is None:
            if not str(options.get("needle", "")):
                self._announce("Type something to find")
            return False
        self._find_options = dict(options)
        text = self.control.GetValue()
        start, end = self.control.GetSelection()
        from_pos = start if reverse else (end if end > start else start)
        match, wrapped = find_next(compiled, text, from_pos=from_pos, backwards=reverse)
        if match is None:
            self._announce(f"Not found: {options.get('needle')}")
            return False
        # A search hit is a jump like any other, and the one people most often
        # want to come back from: F3 walks you away from what you were writing.
        self._record_location()
        self.control.SetSelection(match.start, match.end)
        self.control.ShowPosition(match.start)
        self.control.SetFocus()
        self._touch_status()
        if wrapped:
            # The one thing the reader cannot know: that the search went past
            # the end and started again. Without it, a single match reads as
            # "nothing happened" every time F3 is pressed.
            self._announce("Wrapped to the end" if reverse else "Wrapped to the start")
        return True

    def _match_count(self, options: dict[str, Any]) -> tuple[int, bool] | None:
        """``(count, truncated)`` for *options*, or ``None`` if it cannot run."""
        compiled = self._query(options)
        if compiled is None:
            return None
        return count_matches(compiled, self.control.GetValue())

    def peek_match_count(self, options: dict[str, Any]) -> str:
        """A spoken summary of how many matches *options* has, for the dialog.

        This is the half of searching a listener otherwise cannot get: one
        match and no matches sound identical when you are pressing F3 in the
        dark, and knowing the shape of the answer before committing to it is
        the whole reason the count exists.
        """
        if not str(options.get("needle", "")):
            return ""
        counted = self._match_count(options)
        if counted is None:
            return ""
        count, truncated = counted
        if count == 0:
            return "No matches"
        more = " or more" if truncated else ""
        return f"{count}{more} match{'es' if count != 1 else ''}"

    def cmd_count_occurrences(self) -> None:
        """Say how many times the last search appears in this document."""
        options = dict(self._find_options)
        if not options.get("needle"):
            selected = self._selected_or_last_needle()
            if not selected:
                self._announce("Search for something first, then count it")
                return
            options["needle"] = selected
        summary = self.peek_match_count(options)
        needle = options.get("needle")
        self._announce(f"{summary} for {needle}" if summary else f"Not found: {needle}")

    def cmd_find_all(self) -> None:
        """List every match, so the search's shape can be read rather than walked."""
        options = dict(self._find_options)
        if not options.get("needle"):
            selected = self._selected_or_last_needle()
            if not selected:
                self._announce("Search for something first, then list the matches")
                return
            options["needle"] = selected
        compiled = self._query(options)
        if compiled is None:
            return
        text = self.control.GetValue()
        matches, truncated = all_matches(compiled, text)
        if not matches:
            self._announce(f"Not found: {options.get('needle')}")
            return
        rows = [
            (
                f"Line {match.line}, column {match.column}: {context_sentence(text, match)}",
                match.start,
            )
            for match in matches
        ]
        chosen = choose_match(self, rows, truncated=truncated)
        if chosen is None:
            self.control.SetFocus()
            return
        self._record_location()
        self.control.SetSelection(chosen, chosen + len(matches[0].text))
        self.control.ShowPosition(chosen)
        self.control.SetFocus()
        self._touch_status()

    def cmd_replace(self) -> None:
        ReplaceDialog(
            self,
            self._selected_or_last_needle(),
            self._do_find,
            self._do_replace,
            self._do_replace_all,
        ).Show()

    def _do_replace(self, options: dict[str, Any]) -> None:
        """Replace the match the selection is on, then move to the next one."""
        compiled = self._query(options)
        if compiled is None:
            if not str(options.get("needle", "")):
                self._announce("Type something to find")
            return
        pattern = compiled.pattern
        start, end = self.control.GetSelection()
        selected = self.control.GetValue()[start:end]
        if pattern is not None and end > start and pattern.fullmatch(selected):
            self.control.Replace(start, end, str(options.get("replacement", "")))
            self._set_modified(True)
        self._do_find(options, False)

    def _do_replace_all(self, options: dict[str, Any]) -> None:
        """Replace every match, from the end backwards so offsets stay valid."""
        compiled = self._query(options)
        if compiled is None:
            if not str(options.get("needle", "")):
                self._announce("Type something to find")
            return
        pattern = compiled.pattern
        if pattern is None:
            return
        if self.editor.mode == RICH:
            answer = show_message_box(
                "Replace all in a rich text document removes formatting on the "
                "replaced text. Continue?",
                APP_NAME,
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self,
            )
            if answer != wx.YES:
                return
        replacement = str(options.get("replacement", ""))
        count = 0
        # Backwards, and through Replace rather than by rewriting the value, so
        # every change is one undo step the user can walk back out of.
        for match in reversed(list(pattern.finditer(self.control.GetValue()))):
            self.control.Replace(match.start(), match.end(), replacement)
            count += 1
        if count:
            self._set_modified(True)
        self._announce(f"Replaced {count} occurrence{'s' if count != 1 else ''}")

    # ------------------------------------------------------------------ #
    # Navigate
    # ------------------------------------------------------------------ #

    def _navigate_heading(self, *, reverse: bool) -> None:
        if self.editor.mode != RICH:
            self._announce("Headings are only available in rich text")
            return
        found = self.editor.next_heading(self.control.GetInsertionPoint(), reverse=reverse)
        if found is None:
            self._announce("No previous heading" if reverse else "No next heading")
            return
        start, level = found
        self._go_to(start)
        # The level *and* the text: the level alone says what shape the document
        # is, not where in it the caret has landed.
        self._announce(f"Heading {level}: {self.editor.paragraph_text_at(start)}")

    def cmd_next_heading(self) -> None:
        self._navigate_heading(reverse=False)

    def cmd_previous_heading(self) -> None:
        self._navigate_heading(reverse=True)

    def cmd_list_headings(self) -> None:
        if self.editor.mode != RICH:
            self._announce("Headings are only available in rich text")
            return
        headings = self.editor.all_headings()
        if not headings:
            self._announce("No headings in this document")
            return
        target = choose_heading(self, headings)
        if target is None:
            self.control.SetFocus()
            return
        self._go_to(target)

    # ------------------------------------------------------------------ #
    # Window and help
    # ------------------------------------------------------------------ #

    def cmd_next_window(self) -> None:
        self.app.cycle(self, 1)

    def cmd_previous_window(self) -> None:
        self.app.cycle(self, -1)

    def cmd_next_window_mdi(self) -> None:
        """Ctrl+F6, the Windows MDI convention. The same move as Ctrl+Tab.

        Both are bound rather than one: Ctrl+F6 is what the platform documents
        and what a long-time Windows user reaches for, Ctrl+Tab is what everyone
        else presses, and a key somebody expects and does not get is
        indistinguishable from a broken app.
        """
        self.app.cycle(self, 1)

    def cmd_context_help(self) -> None:
        """What this window is for, then what the focused control does."""
        from quill.ui import app_context_help

        app_context_help.show_help(self)

    def cmd_shortcuts(self) -> None:
        show_text_window(self, "Keyboard shortcuts", shortcut_text())

    def cmd_about(self) -> None:
        body = (
            f"{APP_NAME} {APP_VERSION}\n\n"
            "A small notepad and wordpad replacement for screen reader users.\n"
            "Numbered documents in one window. Plain text or rich text, and\n"
            "nothing else.\n\n"
            "QuillLite is a companion to QUILL for All, not a replacement for it. "
            "AI, dictation, conversion, comparison, publishing and extensions all\n"
            "live in QUILL.\n\n"
            "Part of the QuillVille family by Community Access and BITS (MIT licence).\n"
            "https://github.com/Community-Access/quill\n\n"
            f"Settings and recovered work: {self.app.data_dir}"
        )
        show_text_window(self, f"About {APP_NAME}", body)
