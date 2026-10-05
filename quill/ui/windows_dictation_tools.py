"""Dictation's second row of commands, shared by QUILL and QUILL Lite.

The 2026-09-28 pass (dict.md 2.2, 2.8, 3.1, 3.3, 5) gave dictation more
than :mod:`windows_dictation_commands` had room for, so the new commands are
a second mixin that the first inherits: every host that has Dictation On
has these too, on the same chords.

* **Recent Phrases** (Shift+F11): the last twenty phrases dictated this
  session, newest first, with Insert Again and Copy -- the rescue for a
  "scratch that" that went one too far. Memory only; gone when the app closes.
* **My Words and Phrases** (Alt+Shift+F10): the window that edits
  ``dictation.md`` -- words to spell your way, phrases that expand, and
  corrections for what the engine keeps hearing wrong -- so nobody edits a
  file. The Dictation Settings button opens the same window.
* **Escape** cancels the phrase being heard (the controller decides whether
  there is one; otherwise the key passes on untouched).
* **Ctrl+F11 in a text field** -- Find, Replace, the AI pad's question --
  dictates into that field: :func:`bind_field_dictation` gives a dialog the
  chord and the Escape, pointed at whichever registered field has focus.
* **One session at a time**: Ctrl+F11 in a second document while dictation
  runs in the first moves it there and says so, instead of stopping.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["DictationToolsMixin", "bind_field_dictation"]


def _shared() -> Any:
    from quill.ui import windows_dictation_commands

    return windows_dictation_commands


class DictationToolsMixin:
    """Recent phrases, the words window, the Escape and the field chord."""

    # -- hooks --------------------------------------------------------------- #

    def _dictation_document_name(self) -> str:
        """What "Dictation moved to ..." calls this window's document."""
        name = getattr(self, "document_name", None)
        try:
            text = name() if callable(name) else ""
        except Exception:  # noqa: BLE001 - a name is a courtesy
            text = ""
        return str(text) or "this document"

    # -- commands ------------------------------------------------------------ #

    def cmd_dictation_recent(self) -> None:
        """The last twenty phrases, newest first: insert one again, or copy it."""
        from quill.ui.windows_dictation_dialog import RecentPhrasesDialog

        shared = _shared()
        controller = shared._controller
        phrases = list(controller.recent) if controller is not None else []
        if not phrases:
            self._dictation_say("Nothing has been dictated yet this session.")  # type: ignore[attr-defined]
            return
        dialog = RecentPhrasesDialog(self._dictation_parent(), phrases)  # type: ignore[attr-defined]
        try:
            answer = self._dictation_run_modal(dialog, "Recent Phrases")  # type: ignore[attr-defined]
            chosen, verb = dialog.chosen, dialog.verb
        finally:
            dialog.Destroy()
        if answer != wx.ID_OK or chosen is None:
            return
        if verb == "copy":
            self._dictation_copy(chosen)
            return
        self._dictation_insert_again(chosen)

    def cmd_dictation_words(self) -> None:
        """Add, edit and remove your words, phrases and corrections in a window."""
        from quill.ui.dictation_words_dialog import DictationWordsDialog

        dialog = DictationWordsDialog(
            self._dictation_parent(),  # type: ignore[attr-defined]
            self._dictation_profile_path(),  # type: ignore[attr-defined]
            say=self._dictation_say,  # type: ignore[attr-defined]
            open_file=self._dictation_open_file,  # type: ignore[attr-defined]
        )
        try:
            self._dictation_run_modal(dialog, "My Words and Phrases")  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    def cmd_dictation_into(self, control: Any) -> None:
        """Ctrl+F11 in a text field: dictate into *control*, or stop if it is."""
        if self._dictation_repeat():  # type: ignore[attr-defined]
            return  # Windows repeating the held key
        shared = _shared()
        preferences = self._dictation_preferences()  # type: ignore[attr-defined]
        if preferences.engine == "voice_typing":
            self._dictation_voice_typing()  # type: ignore[attr-defined]
            return
        controller = self._dictation_controller()  # type: ignore[attr-defined]
        if controller.active and shared._host is self and self._dictation_targeted() is control:
            self._dictation_press(controller)  # type: ignore[attr-defined]
            return
        self._dictation_target(self, control=control)  # type: ignore[attr-defined]
        if controller.active:
            self._dictation_say("Dictation moved to this field.")  # type: ignore[attr-defined]
            return
        self._dictation_press(controller)  # type: ignore[attr-defined]

    # -- keys ------------------------------------------------------------------ #

    def _dictation_cancel_key(self, event: Any) -> None:
        """EVT_CHAR_HOOK: Escape while a phrase is being heard throws it away."""
        if event.GetKeyCode() == wx.WXK_ESCAPE and self._dictation_cancel_phrase():
            return  # consumed: the phrase is gone and "Cancelled" was said
        event.Skip()

    def _dictation_cancel_phrase(self) -> bool:
        """``True`` when a phrase being heard for this window was thrown away."""
        shared = _shared()
        controller = shared._controller
        if controller is None or shared._host is not self:
            return False
        if controller.muted:  # Escape while the AI's reply is read: listen now
            controller.unmute()
            self._dictation_say("Listening.")  # type: ignore[attr-defined]
            return True
        return bool(controller.cancel_phrase())

    # -- plumbing ---------------------------------------------------------------- #

    def _dictation_targeted(self) -> Any:
        """The control dictation writes into for this host: a field, or the document."""
        return getattr(self, "_dictation_targeted_control", None) or self._dictation_control()  # type: ignore[attr-defined]

    def _dictation_insert_again(self, text: str) -> None:
        control = self._dictation_targeted()
        try:
            start, end = control.GetSelection()
            replace_as_one_undo(control, int(start), int(end), text)
            control.SetFocus()
        except Exception as error:  # noqa: BLE001 - reported, never raised
            self._dictation_say(f"That could not be inserted. {error}")  # type: ignore[attr-defined]
            return
        self._dictation_after_edit()  # type: ignore[attr-defined]
        self._dictation_say(f"Inserted: {text}")  # type: ignore[attr-defined]

    def _dictation_copy(self, text: str) -> None:
        try:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                finally:
                    wx.TheClipboard.Close()
        except Exception as error:  # noqa: BLE001 - the clipboard is another app's too
            self._dictation_say(f"That could not be copied. {error}")  # type: ignore[attr-defined]
            return
        self._dictation_say(f"Copied: {text}")  # type: ignore[attr-defined]


def bind_field_dictation(window: Any, fields: list[Any], host: Any) -> None:
    """Give *window* Ctrl+F11 (dictate into the focused one of *fields*) and
    Escape (cancel the phrase being heard) while it is open.

    *host* is the document window whose dictation the field borrows, so the
    same engine, settings and words apply, and closing the field's window
    stops dictation the way closing a document does (the control's destroy
    event, bound by ``_dictation_target``).
    """
    fields = [field for field in fields if field is not None]
    if not fields or not all(
        callable(getattr(window, name, None)) for name in ("Bind", "SetAcceleratorTable")
    ):
        return  # a stand-in window (tests), or nothing to dictate into
    # The toggle's default chord (quill/core/keymap.py, tools.windows_dictation_toggle):
    # a dialog has no keymap of its own to consult, and the field chord is the
    # document chord by design -- one key, wherever the cursor is.
    into_id = wx.NewIdRef()

    def _into(_event: Any) -> None:
        focused = wx.Window.FindFocus()
        target = focused if focused in fields else fields[0]
        host.cmd_dictation_into(target)

    window.Bind(wx.EVT_MENU, _into, id=into_id)
    entries = [wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_F11, into_id)]
    existing = getattr(window, "_quill_accelerators", None)
    if isinstance(existing, list):
        entries = existing + entries
    window._quill_accelerators = entries
    window.SetAcceleratorTable(wx.AcceleratorTable(entries))
    window.Bind(wx.EVT_CHAR_HOOK, host._dictation_cancel_key)
