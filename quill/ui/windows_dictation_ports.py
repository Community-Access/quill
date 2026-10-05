"""The two ports dictation's controller writes through, for a wx text control.

Moved out of :mod:`quill.ui.windows_dictation_commands` (GATE-11) when the
2026-10-05 pass gave each one more to do:

* :class:`EditorDocument` -- the document port: one text control, reached
  through its host. New: the **anchor** (dict.md 2.4), so a phrase goes where
  you started speaking even if the caret moved, or the focus went to another
  window, while it was being recognised.
* :class:`HostFeedback` -- the feedback port: the host's cues, speech and
  status line. New: the **live preview** ("Hearing: ..." in the status bar and
  on a braille display, spoken only when the person asked for it -- GATE-13),
  and **phrase_written**, which tells a field that wants to know -- the AI
  Conversation window's message box, which sends at the pause.

Both editors reach these through the shared commands mixin; nothing here is
QUILL's or QUILL Lite's alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import wx

from quill.core.windows_dictation.controller import DictationState, Moment
from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["EditorDocument", "HostFeedback", "PhraseAnchor", "alive"]

#: How much text in front of the caret the spacing rules look at. A sentence is
#: plenty; the whole document would be a copy of it across the wx boundary for
#: every phrase.
_CONTEXT_CHARS = 80

#: How much text before the anchor is remembered, to notice that the document
#: changed around it while the phrase was being recognised.
_ANCHOR_CHARS = 40

#: How long after a phrase is written its words are read back -- long enough
#: for the editor's own reaction to the edit to have been said first.
_READ_BACK_DELAY_MS = 250


def _shared() -> Any:
    from quill.ui import windows_dictation_commands

    return windows_dictation_commands


def alive(window: Any) -> bool:
    """Whether *window* still exists. A destroyed wx object is falsy."""
    try:
        being_deleted = getattr(window, "IsBeingDeleted", None)
        return bool(window) and not (callable(being_deleted) and being_deleted())
    except Exception:  # noqa: BLE001 - a dead wx object raises on any call
        return False


@dataclass(slots=True)
class PhraseAnchor:
    """Where a phrase started: the selection, and the text just before it --
    which is how a document that changed around it is noticed."""

    start: int
    end: int
    before: str
    #: The person's own selection while the phrase is written at the anchor.
    saved: tuple[int, int] | None = None
    #: The phrase is going into a document that no longer has the focus.
    elsewhere: bool = False
    #: What the document was called when the phrase started.
    name: str = ""


class EditorDocument:
    """The document port: one text control, reached through its host."""

    def __init__(self, host: Any, control: Any, *, background: bool = False) -> None:
        self._host = host
        self._control = control
        #: A live transcript: written into whether or not it has the focus, so
        #: the person can keep working elsewhere (dict.md 3.7).
        self.background = background

    def unavailable_reason(self, *, writing: bool) -> str:
        control = self._control
        if not alive(control) or control is not self._host._dictation_targeted():
            return "Dictation stopped: the document it was writing into has closed or changed."
        if not control.IsEditable():
            return "This document is read-only, so dictation cannot write here."
        if writing and not self.background and wx.Window.FindFocus() is not control:
            return "Dictation stopped because the document no longer has the focus."
        return ""

    # -- the anchor (dict.md 2.4) ------------------------------------------- #

    def anchor(self) -> PhraseAnchor:
        start, end = self._control.GetSelection()
        before = self._control.GetRange(max(0, int(start) - _ANCHOR_CHARS), int(start))
        try:
            name = str(self._host._dictation_document_name())
        except Exception:  # noqa: BLE001 - a name is a courtesy
            name = "this document"
        return PhraseAnchor(int(start), int(end), str(before), name=name)

    def anchored_reason(self, anchor: PhraseAnchor) -> str:
        """Why a phrase that started here cannot be written here now. The focus
        does not matter: the person was speaking into this document."""
        del anchor
        control = self._control
        if not alive(control):
            return "Dictation stopped: the document it was writing into has closed."
        if not control.IsEditable():
            return "This document is read-only, so dictation cannot write here."
        return ""

    def place_at_anchor(self, anchor: PhraseAnchor) -> str:
        """Select where the phrase started. Returns what to tell the person, or
        ``""`` when nothing moved and there is nothing to say."""
        control = self._control
        start, end = (int(value) for value in control.GetSelection())
        focused = wx.Window.FindFocus() is control
        if focused and (start, end) == (anchor.start, anchor.end):
            return ""
        last = int(control.GetLastPosition())
        before = str(control.GetRange(max(0, anchor.start - _ANCHOR_CHARS), anchor.start))
        if anchor.end > last or before != anchor.before:
            if focused:
                return ""  # the place is gone; the caret is where it goes, as ever
            return "The place you started speaking has changed, so the words went at the cursor."
        anchor.saved = (start, end)
        anchor.elsewhere = not focused
        control.SetSelection(anchor.start, anchor.end)
        if anchor.elsewhere:
            return f"Written where you started, in {anchor.name or 'this document'}."
        return "Written where you started."

    def release_anchor(self, anchor: PhraseAnchor) -> None:
        """Put the person's own selection back, moved along by what was written."""
        if anchor.saved is None:
            return
        written_end = int(self._control.GetInsertionPoint())
        shift = written_end - anchor.end
        start, end = anchor.saved
        if start >= anchor.end:
            start, end = start + shift, end + shift
        self._control.SetSelection(start, end)

    # -- editing ------------------------------------------------------------- #

    def single_line(self) -> bool:
        multiline = getattr(self._control, "IsMultiLine", None)
        return callable(multiline) and not multiline()

    def context(self) -> tuple[str, str]:
        control = self._control
        start, end = control.GetSelection()
        before = control.GetRange(max(0, start - _CONTEXT_CHARS), start)
        after = control.GetRange(end, min(end + 2, control.GetLastPosition()))
        return before, after

    def selection(self) -> tuple[int, int]:
        start, end = self._control.GetSelection()
        return int(start), int(end)

    def select(self, start: int, end: int) -> None:
        self._control.SetSelection(start, end)

    def insert(self, text: str) -> tuple[int, int]:
        start, end = self._control.GetSelection()
        return self.replace(int(start), int(end), text)

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        control = self._control
        multiline = getattr(control, "IsMultiLine", None)
        if callable(multiline) and not multiline():
            # A one-line box (Find, the AI question): a new paragraph is a space.
            text = " ".join(text.replace("\n", " ").split()) or text.strip()
        # One undo step per phrase, the same path the AI inserts and paste take
        # (dict.md 2.5): select the range and write over it, which the native
        # control records as one reversible edit -- Remove then WriteText was two.
        replace_as_one_undo(control, start, end, text)
        self._edited()
        return start, control.GetInsertionPoint()

    def _edited(self) -> None:
        """Tell the host its document changed -- naming the control when it is
        not the one in front (a live transcript in a background tab)."""
        elsewhere = getattr(self._host, "_dictation_background_edit", None)
        if self.background and callable(elsewhere):
            elsewhere(self._control)
            return
        self._host._dictation_after_edit()

    def text_between(self, start: int, end: int) -> str:
        return str(self._control.GetRange(max(0, start), end))

    def remove(self, start: int, end: int) -> None:
        self._control.Remove(start, end)
        self._control.SetInsertionPoint(start)
        self._edited()

    def line_bounds(self) -> tuple[int, int]:
        control = self._control
        caret = control.GetInsertionPoint()
        last = control.GetLastPosition()
        before = control.GetRange(max(0, caret - 4000), caret)
        after = control.GetRange(caret, min(last, caret + 4000))
        start = caret - (len(before) - (before.rfind("\n") + 1))
        newline = after.find("\n")
        end = caret + (newline if newline >= 0 else len(after))
        return start, end

    def last_position(self) -> int:
        return int(self._control.GetLastPosition())

    def undo(self) -> bool:
        control = self._control
        if not control.CanUndo():
            return False
        control.Undo()
        self._host._dictation_after_edit()
        return True


class HostFeedback:
    """The feedback port: the host's own cues, speech and status line."""

    def __init__(self, host: Any) -> None:
        self._host = host
        self._pending: list[str] = []
        self._timer: Any = None

    def has_cue(self, moment: Moment) -> bool:
        try:
            return bool(self._host._dictation_has_cue(_shared().DICTATION_CUES[moment]))
        except Exception:  # noqa: BLE001 - no sound stack is an answer
            return False

    def cue(self, moment: Moment) -> None:
        try:
            self._host._dictation_cue(_shared().DICTATION_CUES[moment])
        except Exception:  # noqa: BLE001 - a cue must never break dictation
            pass

    def say(self, text: str) -> None:
        try:
            self._host._dictation_say(text)
        except Exception:  # noqa: BLE001 - a closing window cannot speak; never crash
            pass

    def say_quietly(self, text: str) -> None:
        """The spoken preview: without interrupting what the reader is saying."""
        try:
            self._host._dictation_say_quietly(text)
        except Exception:  # noqa: BLE001 - a preview is never worth a failure
            pass

    def read_back(self, text: str) -> None:
        """Say what a phrase wrote, a moment after it was written.

        Reported unreliable when it was spoken at once (2026-09-25). Inserting
        text into a focused edit control is itself something a screen reader
        may react to -- the caret moved, the line changed, the editor's own
        caret cues fire off the same text event -- and a sentence handed over in
        the same instant raced all of that, so sometimes it was heard and
        sometimes it was cut off by whatever the reader said next. Speaking it
        after the edit has settled lets it arrive last and interrupt the rest.

        Phrases that land while one is still waiting are joined rather than
        dropped, so quick speech is read back whole, once.
        """
        self._pending.append(text)
        if self._timer is not None:
            return
        try:
            self._timer = wx.CallLater(_READ_BACK_DELAY_MS, self._speak_pending)
        except Exception:  # noqa: BLE001 - no event loop (tests): say it now
            self._speak_pending()

    def _speak_pending(self) -> None:
        self._timer = None
        text, self._pending = " ".join(self._pending).strip(), []
        if text:
            self.say(text)

    def show(self, text: str) -> None:
        try:
            self._host._dictation_status(text)
        except Exception:  # noqa: BLE001 - the status line is a record, not a need
            pass

    def preview(self, text: str) -> None:
        """The live preview: "Hearing: ..." in the status bar and on braille."""
        try:
            self._host._dictation_preview(text)
        except Exception:  # noqa: BLE001 - a preview is never worth a failure
            pass

    def phrase_written(self, text: str) -> None:
        """A phrase went in: a field that sends at the pause hears about it."""
        try:
            self._host._dictation_phrase_written(text)
        except Exception:  # noqa: BLE001 - the phrase is written either way
            pass

    def state_changed(self, state: DictationState) -> None:
        from quill.ui.windows_dictation_silence import note_activity

        note_activity(state, lambda: _shared()._controller)
        if state is DictationState.OFF:
            from quill.ui.windows_dictation_extras import finished_transcript

            finished_transcript(self._host._dictation_targeted())
        self._host._dictation_state_changed(state)

    # -- the 2026-10-05 voice commands (voice_commands.py) --------------------- #

    def library(self) -> Any:
        """The editor's Copy All, Copy Tray, snippets and abbreviations."""
        from quill.ui.windows_dictation_library import DictationLibrary

        return DictationLibrary(self._host)

    def set_speech_language(self, language: str) -> None:
        """Switch the dictation language, and save it (a choice, not a mode)."""
        self._host._dictation_set_speech_language(language)

    def use_context(self, words: tuple[str, ...]) -> str:
        """Pick a saved dictation context by name; what to say about it."""
        return str(self._host._dictation_use_context_by_name(words))

    def show_commands(self) -> None:
        # After the phrase has been handled, not in the middle of it: the list is
        # a modal window, and a modal window opened inside a recogniser callback
        # would hold that callback open until it closed.
        try:
            wx.CallAfter(self._host._dictation_show_commands)
        except Exception:  # noqa: BLE001 - no event loop (tests)
            self._host._dictation_show_commands()
