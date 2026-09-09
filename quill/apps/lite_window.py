"""One document, one window.

Every :class:`DocumentFrame` owns exactly one file and exactly one editor. There
are no tabs, and that is the product rather than a shortcut: a listener's list of
open documents is Alt+Tab, which they already know, instead of a tab strip they
have to learn to navigate. The Window menu mirrors the same list with Alt+1 to
Alt+9 for the impatient.

The menu bar is generated from :data:`quill.core.lite.commands.COMMANDS`, so the
keys the menus advertise, the keys that are bound, and the keys the Keyboard
Shortcuts window lists are one list with one source. The uniqueness rules
(every item has a key; no key or ``&`` mnemonic claimed twice) are asserted
against that table rather than against a screenshot.

The editor surface is QUILL's own -- :class:`~quill.ui.richedit_editing.
RichEditDocument`, the native ``RICHEDIT50W`` whose ``IAccessible`` value NVDA
and JAWS read correctly where a classic EDIT control's is not, with RTF going
through the Text Object Model because ``EM_STREAMIN`` with a Python callback
hard-crashes msftedit. Neither of those was discovered here; both are QUILL's
findings, and QuillLite gets them by using QUILL's surface rather than by
copying it.

The window is assembled from four neighbours, each answering one question:
:mod:`quill.apps.lite_window_menus` builds the bar,
:mod:`quill.apps.lite_window_commands` answers its File and Edit items,
:mod:`quill.apps.lite_window_format` its Format items,
:mod:`quill.apps.lite_window_view` answers its View items, and
:mod:`quill.apps.lite_window_theme` owns mode, theme and font, and
:mod:`quill.apps.lite_window_status` is the status bar. What is left here is
the window itself: its document state, and its file I/O.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import wx

from quill.apps.lite_printing import DocumentPrintMixin
from quill.apps.lite_window_clipboard import DocumentClipboardMixin
from quill.apps.lite_window_commands import DocumentCommandsMixin
from quill.apps.lite_window_format import DocumentFormatCommandsMixin
from quill.apps.lite_window_marks import DocumentMarksMixin
from quill.apps.lite_window_menus import DocumentMenuMixin
from quill.apps.lite_window_selection import DocumentSelectionMixin
from quill.apps.lite_window_spelling import DocumentSpellingMixin
from quill.apps.lite_window_status import DocumentStatusMixin
from quill.apps.lite_window_theme import DocumentAppearanceMixin
from quill.apps.lite_window_tools import DocumentToolsMixin
from quill.apps.lite_window_typing import DocumentTypingMixin
from quill.apps.lite_window_view import DocumentViewCommandsMixin
from quill.core.lite import APP_NAME
from quill.core.lite import recovery as recovery_mod
from quill.core.lite.filetypes import is_rich_path
from quill.core.lite.textfile import decode_text, encode_text, write_bytes_atomic
from quill.core.numbered_bookmarks import BookmarkSet
from quill.io.rtf_safety import scan_rtf_safety
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import PLAIN, RICH, create_richedit_document
from quill.ui.richedit_rtf_surface import RichEditRtfError

__all__ = ["DocumentFrame"]

#: The construction title. The window is retitled after the document as soon as
#: there is one; the catalogue in :mod:`quill.core.lite_surface_help` matches
#: both this and the "<file> - QuillLite (<mode>)" form F1 sees at runtime.
_TITLE = APP_NAME

#: The temp-file suffix a rich save writes beside its target before replacing it.
_TMP_SUFFIX = ".quilllite-tmp"


class DocumentFrame(
    DocumentCommandsMixin,
    DocumentFormatCommandsMixin,
    DocumentViewCommandsMixin,
    DocumentPrintMixin,
    DocumentToolsMixin,
    DocumentMarksMixin,
    DocumentSelectionMixin,
    DocumentClipboardMixin,
    DocumentTypingMixin,
    DocumentSpellingMixin,
    DocumentMenuMixin,
    DocumentAppearanceMixin,
    DocumentStatusMixin,
    wx.MDIChildFrame,
):
    """One window, one document, one editor."""

    def __init__(
        self,
        app: Any,
        path: Path | None = None,
        mode: str | None = None,
        recovery_slot: recovery_mod.RecoverySlot | None = None,
    ) -> None:
        settings = app.settings
        super().__init__(app.shell, wx.ID_ANY, title=_TITLE)
        self.app = app
        #: This document's number inside the shell. Stable for the life of the
        #: window, because a number that changes when a sibling closes is a
        #: number nobody can rely on -- and it is in the title, which is the one
        #: string the screen reader reads on arrival.
        self.number = app.next_document_number()
        self.path: Path | None = None
        self.modified = False
        #: The line ending and codec the open file used, re-applied on save.
        self.newline = "\r\n"
        self.encoding = "utf-8"
        #: True while the window is filling the control itself, so the resulting
        #: EVT_TEXT is not mistaken for the user typing.
        self._loading = False
        self._find_options: dict[str, Any] = {}
        self._find_dialog: wx.Dialog | None = None
        self._slot: recovery_mod.RecoverySlot | None = None
        self._window_menu_items: list[int] = []
        self._check_items: dict[str, wx.MenuItem] = {}
        #: This document's nine numbered places. Per window, in memory: a
        #: bookmark is about where you are in *this* document right now.
        self.bookmarks = BookmarkSet()
        #: The length the bookmarks were last reconciled against, so an edit's
        #: size can be inferred without the control telling us where it changed.
        self._tracked_length = 0
        # Before the menu bar: _sync_check_items reads _live_spelling to set the
        # Check While Typing mark, and a menu built ahead of the state it
        # mirrors would advertise the wrong answer on the very first open.
        self._init_spelling()
        # Before the menu bar too: _sync_check_items reads the extend-mode flag.
        self._init_selection()

        surface = create_richedit_document(
            wx, self, wx.TE_MULTILINE | wx.TE_PROCESS_TAB, mode or settings.default_mode
        )
        self.control: wx.TextCtrl = surface
        self.editor = surface.quill_richedit
        self.control.SetName("Document")
        self._apply_editor_help()
        self._init_status_bar()
        # The editor takes every pixel the status bar does not. A sizer rather
        # than wx.Frame's single-child auto-fit, because there are two children.
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.control, 1, wx.EXPAND)
        layout.Add(self.status_panel, 0, wx.EXPAND)
        self.SetSizer(layout)
        self._build_menus()
        self._apply_editor_font()
        self.apply_theme()
        self.editor.set_word_wrap(settings.word_wrap)

        self.control.Bind(wx.EVT_TEXT, self._on_text)
        self.control.Bind(wx.EVT_TEXT, self._track_bookmarks)
        self.control.Bind(wx.EVT_CHAR, self._on_char)
        # One handler for both, deliberately: it is caret *activity*, not focus,
        # so it is not the focus handler GATE-13 forbids announcing from -- and
        # it announces nothing, it only marks the status bar stale.
        self.control.Bind(wx.EVT_KEY_UP, self._on_caret_moved)
        self.control.Bind(wx.EVT_LEFT_UP, self._on_caret_moved)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self.Bind(wx.EVT_MENU_OPEN, self._on_menu_open)
        # F1 on the frame itself: no show path wraps a main window, so the
        # context-help engine has to be bound here directly.
        from quill.ui import app_context_help

        app_context_help.install(self, wx=wx)

        self._autosave = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_autosave_tick, self._autosave)
        self._autosave.Start(settings.autosave_seconds * 1000)

        # MDI children open maximised, which is what a one-document-at-a-time
        # editor wants: the child fills the shell, so there is no inner window
        # frame to get lost in and nothing to arrange.
        self.Maximize(True)
        if recovery_slot is not None:
            self._load_recovery(recovery_slot)
        elif path is not None:
            self.load(path)
        self._update_title()
        self._touch_status()
        self.control.SetFocus()

    # ------------------------------------------------------------------ #
    # Document state
    # ------------------------------------------------------------------ #

    def document_name(self) -> str:
        return self.path.name if self.path else "Untitled"

    def _update_title(self) -> None:
        """Retitle after the document. The reader announces this; nothing else does."""
        mode = "rich text" if self.editor.mode == RICH else "plain text"
        star = "*" if self.modified else ""
        # The number leads, because it is the handle a person uses to come back
        # here ("document 3"), and because an MDI child is not in Alt+Tab -- so
        # the title is the only place the number can be announced from.
        self.SetTitle(f"{self.number}: {star}{self.document_name()} - {APP_NAME} ({mode})")

    def _set_modified(self, modified: bool) -> None:
        if modified == self.modified:
            return
        self.modified = modified
        self._update_title()
        self._touch_status()
        if modified and self._slot is None:
            self._slot = recovery_mod.new_slot(
                self.editor.mode, str(self.path) if self.path else ""
            )

    def _on_text(self, event: wx.CommandEvent) -> None:
        if not self._loading:
            self._set_modified(True)
        event.Skip()

    def _on_caret_moved(self, event: wx.Event) -> None:
        # The bar refreshes on its own coalescing timer, so a held arrow key
        # costs one recount after the caret stops rather than one per repeat.
        self._touch_status()
        # F8 extend mode rides this hook rather than binding a second handler:
        # the caret has already moved by EVT_KEY_UP, which is exactly when the
        # selection needs stretching to meet it.
        key_code = event.GetKeyCode() if hasattr(event, "GetKeyCode") else 0
        self.extend_selection_after_move(key_code)
        event.Skip()

    def _on_activate(self, event: wx.ActivateEvent) -> None:
        if event.GetActive():
            self.app.active_frame = self
        event.Skip()

    def _report_failure(self, caption: str, message: str) -> None:
        """Report a failure that cost the user something, in a box they must dismiss.

        Not an announcement: a save that did not happen is not a status message,
        and a listener who was looking away would never know. The wrapper adds the
        screen-reader entry and exit cues a raw ``wx.MessageBox`` has none of.
        """
        show_message_box(message, caption, wx.OK | wx.ICON_ERROR, self)

    def _apply_editor_help(self) -> None:
        """What F1 says while the cursor is in the document itself.

        The control a listener is in for all but a few seconds of a session, and
        the one the shared audit cannot see: it is built by
        :func:`~quill.ui.richedit_editing.create_richedit_document`, not
        constructed here, so without this call F1 in the document would answer
        with the generic "a QuillLite window" sentence and nothing else. The
        answer differs by mode, because what you can do here differs by mode --
        so it is re-applied whenever the mode changes.
        """
        shared = (
            " F6 moves to the status bar, which carries the position, the word "
            "count, the encoding and the line endings. Control S saves."
        )
        if self.editor.mode == RICH:
            self.control.SetHelpText(
                "Your document, in rich text. Control B, I and U set bold, italic "
                "and underline; Control Alt 1 to 4 make the paragraph a heading and "
                "Control Alt 0 makes it body text again; Control Alt H and Control "
                "Alt Shift H move between headings, and Control Shift D describes "
                "the formatting where the cursor is." + shared
            )
            return
        self.control.SetHelpText(
            "Your document, in plain text: one font, no formatting, and a paste "
            "arrives as text. This is the mode for notes, code and configuration "
            "files, and it writes back the encoding and the line endings the file "
            "arrived with. Control Shift M switches to rich text." + shared
        )

    def _announce(self, message: str) -> None:
        """Say *message*, and leave it in the status bar to be re-read.

        Only ever the outcome of something the user did -- a save, a formatting
        change, a search that wrapped. Titles, focus moves, control names and
        selection changes are the screen reader's to announce, and saying them
        again is the over-announcing GATE-13 exists to catch.
        """
        self.app.voice.speak(message)
        self._set_status_message(message)

    # ------------------------------------------------------------------ #
    # Load
    # ------------------------------------------------------------------ #

    def load(self, path: Path) -> bool:
        """Open *path* into this window. ``False`` when it could not be read."""
        path = Path(path)
        mode = RICH if is_rich_path(path.name) else PLAIN
        self._loading = True
        try:
            if mode == RICH:
                self._load_rich(path)
            else:
                self._load_plain(path)
        except (OSError, RichEditRtfError) as exc:
            self._loading = False
            self._report_failure("Open failed", f"Could not open {path.name}.\n\n{exc}")
            return False
        finally:
            self._loading = False
        self.path = path
        self._discard_slot()
        self.modified = False
        self._remember(path)
        self.control.SetInsertionPoint(0)
        self._update_title()
        # The file's own name decides whether it is checked, so this has to run
        # after the path is set and not at construction: a window is built
        # empty and only then told which file it holds.
        self._init_spelling()
        self._sync_check_items()
        self._touch_status()
        self.announce_spelling_state_if_skipped()
        return True

    def _load_rich(self, path: Path) -> None:
        """Scan the RTF for unsafe constructs, then hand the safe copy to the TOM."""
        if not self.editor.rtf_available():
            raise RichEditRtfError("Rich text needs the Windows Rich Edit control.")
        report = scan_rtf_safety(path.read_text(encoding="utf-8", errors="replace"))
        self._set_mode_internal(RICH)
        self.editor.set_rtf(report.sanitized_rtf.encode("utf-8", errors="replace"))
        self._apply_rich_theme_colour()
        if report.blocked:
            self._announce("Removed for safety: " + ", ".join(report.blocked))

    def _load_plain(self, path: Path) -> None:
        decoded = decode_text(path.read_bytes())
        self.encoding, self.newline = decoded.encoding, decoded.newline
        self._set_mode_internal(PLAIN)
        self.control.ChangeValue(decoded.text)

    def _load_recovery(self, slot: recovery_mod.RecoverySlot) -> None:
        """Restore a slot into this window, leaving it modified and unsaved."""
        self._loading = True
        try:
            if slot.mode == RICH and self.editor.rtf_available():
                self._set_mode_internal(RICH)
                self.editor.load_rtf(str(slot.content_path))
                self._apply_rich_theme_colour()
            else:
                decoded = decode_text(slot.content_path.read_bytes())
                self.encoding, self.newline = decoded.encoding, decoded.newline
                self._set_mode_internal(PLAIN)
                self.control.ChangeValue(decoded.text)
        except (OSError, RichEditRtfError) as exc:
            self._report_failure("Recovery failed", f"Could not restore {slot.title}.\n\n{exc}")
        finally:
            self._loading = False
        if slot.original_path and Path(slot.original_path).exists():
            self.path = Path(slot.original_path)
        self._slot = slot
        self.modified = True
        self._update_title()
        self._touch_status()

    def _remember(self, path: Path) -> None:
        """Put *path* at the head of the recent list, in every window."""
        self.app.settings.remember_recent(str(path))
        self.app.save_settings()
        self.app.refresh_all_menus()

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def save(self, target: Path | None = None) -> bool:
        """Write the document. Falls through to Save As when it has no name yet."""
        destination = target if target is not None else self.path
        if destination is None:
            return self.cmd_save_as()
        destination = Path(destination)
        try:
            if self.editor.mode == RICH:
                self._write_rtf(destination)
            else:
                write_bytes_atomic(
                    destination,
                    encode_text(
                        self.control.GetValue(),
                        encoding=self.encoding,
                        newline=self.newline,
                    ),
                )
        except (OSError, RichEditRtfError) as exc:
            self._report_failure("Save failed", f"Could not save {destination.name}.\n\n{exc}")
            return False
        if self.app.feature_enabled("backups"):
            # After the real write, never before: a backup that fails must not
            # be able to fail the save it was taken alongside.
            from quill.core.lite.backups import write_backup

            write_backup(destination, self.control.GetValue())
        self.path = destination
        self._discard_slot()
        self._set_modified(False)
        self._update_title()
        # Save As can change the extension, and the extension is what decides
        # whether this document is spell-checked. A .txt saved as .json should
        # go quiet; the taught-word cache is dropped for the same reason, since
        # the document's own sidecar dictionary moved with the name.
        self._forget_spell_dictionary()
        self._remember(destination)
        self._announce(f"Saved {destination.name}")
        return True

    def _write_rtf(self, target: Path) -> None:
        """Save through the TOM to a sibling temp file, then replace the target.

        The theme colour is removed for the duration of the save, so dark mode
        never leaks light grey text into somebody's file, and restored in a
        ``finally`` so a failed save does not leave the window unreadable.
        """
        tmp = target.with_name(target.name + _TMP_SUFFIX)
        self._set_whole_document_colour(None)
        try:
            self.editor.save_rtf(str(tmp))
            os.replace(tmp, target)
        finally:
            self._apply_rich_theme_colour()
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _write_recovery_copy(self) -> None:
        """The autosave tick: copy unsaved work aside. Never raises, never blocks."""
        slot = self._slot
        if slot is None or not self.modified:
            return
        try:
            if self.editor.mode == RICH and slot.mode == RICH:
                tmp = slot.content_path.with_name(slot.content_path.name + _TMP_SUFFIX)
                self._set_whole_document_colour(None)
                try:
                    self.editor.save_rtf(str(tmp))
                finally:
                    self._apply_rich_theme_colour()
                os.replace(tmp, slot.content_path)
            else:
                if slot.mode != self.editor.mode:
                    # The document changed mode since the slot was made; a plain
                    # copy in a .rtf slot would be restored by the RTF reader.
                    recovery_mod.discard(slot)
                    slot = self._slot = recovery_mod.new_slot(
                        self.editor.mode, str(self.path) if self.path else ""
                    )
                write_bytes_atomic(
                    slot.content_path, self.control.GetValue().encode("utf-8", errors="replace")
                )
            slot.original_path = str(self.path) if self.path else ""
            recovery_mod.write_meta(slot)
        except (OSError, RichEditRtfError):
            pass  # the next tick tries again; a failed copy must not interrupt typing

    def _discard_slot(self) -> None:
        if self._slot is not None:
            recovery_mod.discard(self._slot)
            self._slot = None

    def _on_autosave_tick(self, _event: wx.TimerEvent) -> None:
        self._write_recovery_copy()

    def stop_timers(self) -> None:
        """Stop everything that fires on a clock. Safe to call more than once."""
        try:
            self._autosave.Stop()
        except RuntimeError:
            pass
        self._stop_status_timer()

    def restart_autosave(self) -> None:
        """Re-arm the timer at the current interval, after Preferences changes it."""
        self._autosave.Start(self.app.settings.autosave_seconds * 1000)

    # ------------------------------------------------------------------ #
    # Closing
    # ------------------------------------------------------------------ #

    def confirm_discard(self) -> bool:
        """``True`` when it is safe to lose this window's content."""
        if not self.modified:
            return True
        self.Raise()  # ask about the window the question is about
        answer = show_message_box(
            f"Save changes to {self.document_name()}?",
            APP_NAME,
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
            self,
        )
        if answer == wx.YES:
            return self.save()
        return answer == wx.NO

    def _on_close(self, event: wx.CloseEvent) -> None:
        if event.CanVeto() and not self.confirm_discard():
            event.Veto()
            return
        self.stop_timers()
        self._discard_slot()
        self.app.forget_frame(self)
        self.Destroy()

    # ------------------------------------------------------------------ #
