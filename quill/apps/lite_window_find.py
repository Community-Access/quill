"""Find, Find Next, Count Occurrences, Find All and Replace, for QuillLite.

Split out of :mod:`quill.apps.lite_window_commands` on 2026-09-10 for GATE-11.
It was already its own ``# -- find and replace --`` section of a module that
otherwise holds one-screen command handlers, and it is the only part of that
file with a model of its own: a compiled query, a remembered set of options, a
live modeless dialog, and two different sentences for two different kinds of
miss.

Those two sentences are why this is worth reading before changing anything here.
**Wrapping on** gives "Not found: <needle>" -- the fix is to change what you are
looking for. **Wrapping off** gives "No more matches. Reached the end of the
document, and wrapping is off." -- the fix is to go to the other end and press
again. They are different facts, and a listener who is told the first when the
second is true stops searching for a word that is in the document.

The channel that carries them is ``settings.find_not_found_feedback``, resolved
through the shared rule in :mod:`quill.core.action_feedback` so QUILL's
``_report_search_missed`` and this cannot answer differently. Default is the
tone alone: F3 is pressed in runs, and "Not found" spoken on every press is the
fastest way to make somebody turn speech off altogether. The status bar carries
the words in every mode, because it is the record rather than the feedback.
"""

from __future__ import annotations

from typing import Any

import wx

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
from quill.core.lite import APP_NAME
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentFindMixin"]


class DocumentFindMixin:
    """Composed onto ``DocumentFrame`` through ``DocumentCommandsMixin``.

    Reads ``control``, ``_find_options``, ``_find_dialog``, ``app.settings``,
    ``_announce`` and ``_go_to`` from the host, exactly as it did when it was a
    section of the larger module.
    """

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
            # QUILL's setting, honoured here too. QuillLite always wrapped, in
            # both directions, with no way to say otherwise -- and wrapping is not
            # a preference about tidiness: for somebody working down a document by
            # F3, a search that silently starts again at the top has moved them
            # somewhere they did not ask to go, and they find out by reading.
            wrap=bool(getattr(self.app.settings, "wrap_find", True)),
        )
        try:
            return compile_query(query)
        except FindModelError as error:
            self._announce(str(error))
            return None

    def _report_not_found(self, needle: str, *, reverse: bool) -> None:
        """Say a search missed, in whichever channel the user asked for.

        Two different facts, and the wording separates them, because the fix is
        different. With wrapping **on** there is no such text in the document at
        all, and the answer is to change the pattern. With wrapping **off** the
        search has only run out of document in the direction it was going, and the
        answer is to go to the other end and press again -- so the sentence says
        which end it stopped at rather than claiming the text is not there.

        The channel is ``settings.find_not_found_feedback``, defaulting to the tone
        alone: F3 is pressed in runs, and "Not found" spoken on every press of it
        is the fastest way to make somebody switch the speech off altogether. The
        status bar is written whatever the mode, because it is the record.
        """
        from quill.core.action_feedback import resolve
        from quill.core.sound_events import SoundEvent

        if getattr(self.app.settings, "wrap_find", True):
            message = f"Not found: {needle}"
        else:
            edge = "start" if reverse else "end"
            message = f"No more matches. Reached the {edge} of the document, and wrapping is off."
        play, speak = resolve(
            getattr(self.app.settings, "find_not_found_feedback", "sound"),
            has_sound=self._has_sound_for(SoundEvent.SEARCH_NOT_FOUND),
        )
        if play:
            self._cue(SoundEvent.SEARCH_NOT_FOUND)
        if speak:
            self.app.voice.speak(message)
        self._set_status_message(message)

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
        from quill.core.sound_events import SoundEvent

        if match is None:
            self._report_not_found(str(options.get("needle", "")), reverse=reverse)
            return False
        # A search hit is a jump like any other, and the one people most often
        # want to come back from: F3 walks you away from what you were writing.
        self._record_location()
        self.control.SetSelection(match.start, match.end)
        self.control.ShowPosition(match.start)
        self.control.SetFocus()
        self._touch_status()
        # Wrapping is its own cue, not "found" twice: going past the end and
        # starting again is the one thing the reader cannot know, and a single
        # match otherwise reads as "nothing happened" on every press of F3.
        self._cue(SoundEvent.SEARCH_WRAPPED if wrapped else SoundEvent.SEARCH_FOUND)
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
        """Say how many times the last search appears in this document.

        With nothing searched for yet, this *asks* rather than refusing: the
        Find dialog opens on an empty box, which is the thing the command needed
        anyway. It is also why the row is never greyed out. A disabled menu item
        keeps showing its key and stops dispatching it, so Alt+Ctrl+Shift+F3
        would go from "search for something first" to doing nothing at all and
        saying nothing about it -- and a key that is silently dead is the one
        failure this app's menu rules exist to prevent.
        """
        options = dict(self._find_options)
        if not options.get("needle"):
            selected = self._selected_or_last_needle()
            if not selected:
                self.cmd_find()
                return
            options["needle"] = selected
        summary = self.peek_match_count(options)
        needle = options.get("needle")
        self._announce(f"{summary} for {needle}" if summary else f"Not found: {needle}")

    def cmd_find_all(self) -> None:
        """List every match, so the search's shape can be read rather than walked.

        Opens Find when there is nothing to list yet, for the reason
        :meth:`cmd_count_occurrences` explains.
        """
        options = dict(self._find_options)
        if not options.get("needle"):
            selected = self._selected_or_last_needle()
            if not selected:
                self.cmd_find()
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
        # The chosen match's own length, not the first one's. A regular
        # expression matches runs of different lengths, so jumping to the fifth
        # hit selected however many characters the *first* hit had been -- which
        # for a listener is a selection whose end is somewhere they did not ask
        # for, and for Ctrl+X is the wrong text.
        lengths = {match.start: len(match.text) for match in matches}
        self._record_location()
        self.control.SetSelection(chosen, chosen + lengths.get(chosen, 0))
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
        text = self.control.GetValue()
        count = len(list(pattern.finditer(text)))
        if count:
            self._replace_every_match(pattern, replacement, text)
            self._set_modified(True)
        self._announce(f"Replaced {count} occurrence{'s' if count != 1 else ''}")

    def _replace_every_match(self, pattern: Any, replacement: str, text: str) -> None:
        """Apply every replacement -- in **one** undo step where that is possible.

        Plain text takes a single ``Replace`` over the whole document, so
        **Ctrl+Z once puts it all back**, the way QUILL's Replace All and every
        editor people arrive from behave. It used to be one ``Replace`` per
        match, on the argument that each should be separately undoable; that is
        the wrong shape for this command. Walking back out of two hundred
        replacements one at a time is not a feature -- you cannot see which one
        you are on, there is nothing to stop at, and for a listener the two
        hundredth press is indistinguishable from the hundredth.

        **Rich text keeps the per-match loop, and that is a real trade rather
        than an oversight.** Rewriting the whole range would flatten every bold
        run and heading in the document, not just the text being replaced -- far
        more than the confirmation above warns about. So formatting wins there
        and the undo stack stays long; the dialog already asks first.

        Backwards in both cases, so an earlier replacement cannot shift the
        offsets of a later one.
        """
        if self.editor.mode == RICH:
            for match in reversed(list(pattern.finditer(text))):
                self.control.Replace(match.start(), match.end(), replacement)
            return
        self.control.Replace(0, self.control.GetLastPosition(), pattern.sub(replacement, text))
