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

import wx

from quill.apps.lite_dialogs import show_text_window
from quill.apps.lite_window_find import DocumentFindMixin
from quill.apps.lite_window_go_to import DocumentGoToMixin
from quill.apps.lite_window_settings_backup import DocumentSettingsBackupMixin
from quill.apps.lite_window_special_character import DocumentSpecialCharacterMixin
from quill.core.datetime_insert import NOTEPAD_DATETIME_FORMAT
from quill.core.lite import APP_NAME, APP_VERSION
from quill.core.lite.commands import shortcut_text
from quill.core.lite.filetypes import (
    OPEN_WILDCARD,
    SAVE_WILDCARD_PLAIN,
    SAVE_WILDCARD_RICH,
    is_rich_path,
)
from quill.core.lite.keymap import key_for, spoken_key_for
from quill.core.support_message import SUPPORT_EMAIL
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import (
    PLAIN,
    RICH,
)

__all__ = ["DocumentCommandsMixin"]

#: Date and time, in the order most of the English-speaking world writes it.
#: In core since 2026-09-16, so QUILL's F5 writes the same stamp (bad.md P1.9).
_DATETIME_FORMAT = NOTEPAD_DATETIME_FORMAT


class DocumentCommandsMixin(
    DocumentFindMixin,
    DocumentGoToMixin,
    DocumentSpecialCharacterMixin,
    DocumentSettingsBackupMixin,
):
    """The ``cmd_*`` handlers the command table names.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``control``, ``editor``, ``app``, ``path``, ``_announce`` and the document
    state these read and change.

    Find and Replace moved to :class:`~quill.apps.lite_window_find.DocumentFindMixin`
    on 2026-09-10 (GATE-11) and are inherited here, so ``DocumentFrame`` and
    every command-table row are unchanged. They went because they are the one
    part of this file with a model of their own rather than a handler that reads
    the control and says a sentence.
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
        elif not wants_rich and rich:
            if not self._confirm_flatten_to_plain():
                return False
            # The *file* is flattened first and the window only afterwards, and
            # only if the write worked. It used to ChangeValue the buffer here,
            # leave self.path pointing at the old .rtf, and then try the save --
            # so a locked file or a full disk left the window holding flattened
            # text under the rich name, with the next Ctrl+S ready to write it
            # over the original. ChangeValue is off the undo stack, so the
            # formatting was gone from the window too (bad.md F1).
            if not self.save(target, text=self.control.GetValue()):
                return False
            self._apply_flatten_to_plain()
            return True
        # A .md target converts an HTML document rather than renaming it, which
        # is what the Markdown row in the type list promises. Planned here and
        # applied after the write, for the same reason.
        markdown = self.plan_markdown_conversion(target)
        if markdown is not None:
            if not self.save(target, text=markdown):
                return False
            self.apply_markdown_conversion(markdown)
            return True
        return self.save(target)

    def _confirm_flatten_to_plain(self) -> bool:
        """Ask before a Save As that throws the formatting away. Asks only.

        The flattening itself is :meth:`_apply_flatten_to_plain`, after the
        write: a conversion applied to the buffer before the file is written is
        one a failed write cannot take back (bad.md F1).
        """
        answer = show_message_box(
            "Saving as plain text removes all formatting. Continue?",
            APP_NAME,
            # NO_DEFAULT because this loses formatting: a listener pressing Enter
            # reflexively must not be the one who throws it away.
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self,
        )
        return answer == wx.YES

    def _apply_flatten_to_plain(self) -> None:
        """Make the window plain text, now that the plain file is on disk."""
        text = self.control.GetValue()
        self._loading = True
        try:
            self._set_mode_internal(PLAIN)
            self.control.ChangeValue(text)
            self.doc_text.invalidate()  # ChangeValue raises no text event
            self.apply_theme()
        finally:
            self._loading = False

    def cmd_close(self) -> None:
        self.Close()

    def cmd_exit(self) -> None:
        self.app.exit_all()

    # ------------------------------------------------------------------ #
    # Edit
    # ------------------------------------------------------------------ #

    def _cue(self, event: str) -> None:
        """Play an earcon for something the screen reader says nothing about.

        Which is the whole justification for putting sounds on these six
        commands. Cut, copy, paste, delete, undo and redo change the document
        and change *nothing a reader announces*: focus does not move, no control
        gains a name, and speaking "copied" on every Ctrl+C would be intolerable
        within a minute. So the feedback is a sound or it is nothing, and for a
        listener it has been nothing.

        Silent when the area is off, when the pack has no such sound, or when
        there is no audio at all -- never an error. A cue that could break a
        paste would be worse than no cue.
        """
        from quill.ui.companion_cues import post_cue

        post_cue(event)

    def cmd_undo(self) -> None:
        from quill.core.sound_events import SoundEvent

        if self.control.CanUndo():
            self.control.Undo()
            self._action(SoundEvent.UNDO_PERFORMED, "Undone")
        else:
            # Its own sound, and one that does not move in pitch, because the
            # undo stack did not move either. The words still come too: this is
            # the one of the six where something *failed*, and a listener should
            # not have to interpret a tone to find that out.
            self._cue(SoundEvent.NOTHING_TO_UNDO)
            self._announce("Nothing to undo")

    def cmd_redo(self) -> None:
        from quill.core.sound_events import SoundEvent

        if self.control.CanRedo():
            self.control.Redo()
            self._action(SoundEvent.REDO_PERFORMED, "Redone")
        else:
            self._cue(SoundEvent.NOTHING_TO_UNDO)
            self._announce("Nothing to redo")

    # Cut, copy and paste post nothing themselves. Their feedback is bound to
    # wx's own clipboard events in DocumentClipboardMixin.bind_clipboard_cues,
    # so it arrives once whichever of the four routes was taken -- including the
    # control's own key handling, which never comes through here at all.
    def cmd_cut(self) -> None:
        self.control.Cut()

    def cmd_copy(self) -> None:
        self.control.Copy()

    def cmd_paste(self) -> None:
        """Paste. In a plain text document that means *plain* text, always.

        The control is a Rich Edit whatever the document is (see
        ``RichEditDocument.set_text_mode`` for why it is no longer put into the
        control's own plain-text mode), so a straight Paste into a plain
        document would bring bold and colours in with it -- and then drop them,
        without a word, at the next save. Pasting as text is what "plain text
        document" means; Ctrl+Shift+V is for the other case, in rich documents.
        """
        if self.editor.mode != RICH:
            self.cmd_paste_plain()
            return
        self.control.Paste()

    def cmd_delete(self) -> None:
        """Notepad's Edit > Delete: remove the selection, or the next character.

        The Del key already does this inside the control. The menu item exists
        because a menu is how somebody finds out that it does, and because
        Notepad has had the item since 1985.
        """
        from quill.core.sound_events import SoundEvent

        start, end = self.control.GetSelection()
        if end > start:
            self.control.Remove(start, end)
        else:
            self.control.Remove(start, min(start + 1, self.control.GetLastPosition()))
        self._action(SoundEvent.TEXT_DELETED, "Deleted")

    def cmd_select_all(self) -> None:
        """Select the lot. Announced by the reader, so not announced here.

        The status touch is not optional though: the bar carries a Selection cell
        reading "N words, N characters selected", and Ctrl+A was the one way of
        selecting that never told it to recount -- so the cell went on saying "No
        selection" over a fully selected document.
        """
        self.control.SelectAll()
        self._touch_status()

    def cmd_insert_datetime(self) -> None:
        """Notepad's F5: put the time and date in at the caret, and read it back.

        The read-back is the whole accessibility of the command. A screen reader
        says nothing when an app writes text on its own behalf -- no focus moved
        and no control was named -- so without this, F5 was a keystroke after
        which something had silently appeared, and finding out what meant
        arrowing back over it character by character.

        **QUILL grew an F5 of its own on 2026-09-16**, reversing the 2026-09-10
        reading of "QuillLite may never be ahead of QUILL". That reading was
        that QUILL's bundled ``com.quill.bundled.insert-tools`` Quillin already
        put three variants on Insert > Date and Time, so a second inserter would
        undo a consolidation for nothing. What it missed is the key: those three
        are menu rows reached through a submenu, and F5 is the chord a person
        arrives with. The Quillin's three variants stay; QUILL's F5 is one
        command in core (``edit.insert_date_time``), which also closes the gap
        the old reading named and shrugged at -- **Safe Mode** switches Quillin
        contributions off, and there QUILL had no date insert at all.

        The stamp itself is :data:`~quill.core.datetime_insert.NOTEPAD_DATETIME_FORMAT`
        so the two editors cannot drift apart on what F5 writes (bad.md P1.9).
        """
        stamp = time.strftime(_DATETIME_FORMAT)
        self.control.WriteText(stamp)
        self._set_modified(True)
        self._announce(f"Inserted {stamp}")
        self._touch_status()

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

    # ------------------------------------------------------------------ #
    # Naming a key in a sentence
    # ------------------------------------------------------------------ #

    def key_for(self, handler: str) -> str:
        """The chord *handler* answers to right now, or "" if it has none."""
        return key_for(getattr(self.app, "keymap", None), handler)

    def spoken_key_for(self, handler: str) -> str:
        """:meth:`key_for`, as a sentence says it -- "Control Alt Y"."""
        return spoken_key_for(getattr(self.app, "keymap", None), handler)

    # ------------------------------------------------------------------ #
    # Window and help
    # ------------------------------------------------------------------ #

    def cmd_next_window(self) -> None:
        self.app.cycle(self, 1)

    def cmd_previous_window(self) -> None:
        self.app.cycle(self, -1)

    def cmd_close_mdi(self) -> None:
        """Ctrl+F4, the Windows MDI convention. The same move as Ctrl+W.

        Both are bound rather than one, for the reason Ctrl+F6 and Ctrl+Tab both
        are: a key somebody expects and does not get is indistinguishable from a
        broken app, and Ctrl+F4 has closed an MDI child since Windows 3.1.
        """
        self.cmd_close()

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
        show_text_window(self, "Keyboard shortcuts", shortcut_text(self.app.keymap))

    def cmd_get_help_from_support(self) -> None:
        """Write to support, with QuillLite's own name on the message."""
        from quill.ui.support_dialog import open_support_message

        open_support_message(self, source_app=APP_NAME, app_version=APP_VERSION)

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
            f"Settings and recovered work: {self.app.data_dir}\n\n"
            f"Support: {SUPPORT_EMAIL}"
        )
        show_text_window(self, f"About {APP_NAME}", body)
