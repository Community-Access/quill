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

from pathlib import Path
from typing import Any

import wx

from quill.apps.lite_keymap_editor import DocumentKeymapMixin
from quill.apps.lite_printing import DocumentPrintMixin
from quill.apps.lite_updates import DocumentUpdatesMixin
from quill.apps.lite_window_clipboard import DocumentClipboardMixin
from quill.apps.lite_window_commands import DocumentCommandsMixin
from quill.apps.lite_window_context_menu import DocumentContextMenuMixin
from quill.apps.lite_window_file import DocumentFileMixin
from quill.apps.lite_window_format import DocumentFormatCommandsMixin
from quill.apps.lite_window_history import DocumentHistoryMixin
from quill.apps.lite_window_lines import DocumentLineMixin
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
from quill.core.locations import LocationRing
from quill.core.numbered_bookmarks import BookmarkSet
from quill.core.sound_events import SoundEvent
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import RICH, create_richedit_document

__all__ = ["DocumentFrame"]

#: The construction title. The window is retitled after the document as soon as
#: there is one; the catalogue in :mod:`quill.core.lite_surface_help` matches
#: both this and the "<file> - QuillLite (<mode>)" form F1 sees at runtime.
_TITLE = APP_NAME


class DocumentFrame(
    DocumentCommandsMixin,
    DocumentFormatCommandsMixin,
    DocumentViewCommandsMixin,
    DocumentPrintMixin,
    DocumentUpdatesMixin,
    DocumentToolsMixin,
    DocumentKeymapMixin,
    DocumentLineMixin,
    DocumentHistoryMixin,
    DocumentMarksMixin,
    DocumentSelectionMixin,
    DocumentClipboardMixin,
    DocumentTypingMixin,
    DocumentSpellingMixin,
    DocumentFileMixin,
    DocumentContextMenuMixin,
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
        # No system menu, and that single missing style is what keeps the menu
        # bar readable. A *maximised* MDI child -- which is how every document
        # here opens -- has Windows insert the child's system menu into the
        # parent's menu bar as a bitmap at the far left, plus minimise, restore
        # and close bitmaps at the far right. None of the four carries text, and
        # a screen reader announces that leading one as **"Document"** -- so
        # pressing Alt landed on "Document" instead of File, and Alt+F opened
        # the File menu while the bar said something else entirely. Dropping
        # WS_SYSMENU removes all four; the child still maximises (which
        # dropping the maximise box would prevent), still has its caption, and
        # is still closed with Ctrl+W, Alt+F4 or File > Close Window.
        super().__init__(
            app.shell,
            wx.ID_ANY,
            title=_TITLE,
            style=wx.DEFAULT_FRAME_STYLE & ~wx.SYSTEM_MENU,
        )
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
        #: Where the caret has been, so a jump can be taken back. QUILL's own
        #: ring (quill/core/locations.py), fed from the one seam every jump
        #: goes through -- see DocumentCommandsMixin._go_to. Per window and in
        #: memory: "where I was a moment ago" is a fact about this session,
        #: unlike the bookmarks above, which are about the document.
        self.locations = LocationRing()
        #: The length the bookmarks were last reconciled against, so an edit's
        #: size can be inferred without the control telling us where it changed.
        self._tracked_length = 0
        # Before _init_spelling, which is the first thing that asks whether a
        # word is being ignored: the list has to exist before anything reads it.
        self._init_context_menu()
        # Before the menu bar: _sync_check_items reads _live_spelling to set the
        # Check While Typing mark, and a menu built ahead of the state it
        # mirrors would advertise the wrong answer on the very first open.
        self._init_spelling()
        # Before the menu bar too: _sync_check_items reads the extend-mode flag.
        self._init_selection()
        # And the overtype mirror, for the same reason: the Overwrite Mode mark
        # is read while the bar is built.
        self._init_overwrite()

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
        # Watching the Insert key go past to the control, which does the
        # overtype itself. Never a binding: Insert is the screen reader's
        # modifier. See DocumentTypingMixin._on_key_down.
        self.control.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        # One handler for both, deliberately: it is caret *activity*, not focus,
        # so it is not the focus handler GATE-13 forbids announcing from -- and
        # it announces nothing, it only marks the status bar stale.
        self.control.Bind(wx.EVT_KEY_UP, self._on_caret_moved)
        self.control.Bind(wx.EVT_LEFT_UP, self._on_caret_moved)
        # The Applications key and the right mouse button, one handler. Replaces
        # the native TextCtrl menu, which cannot know anything about the word
        # under the caret -- see DocumentContextMenuMixin.
        self.control.Bind(wx.EVT_CONTEXT_MENU, self._on_editor_context_menu)
        # Cut, copy and paste, from wx's own events rather than from the three
        # commands -- so the control's own Ctrl+C is reported too, which a cue
        # inside cmd_copy could never see. See bind_clipboard_cues.
        self.bind_clipboard_cues()
        # A document arriving and a document going are two of the four moments
        # a desktop has always had a sound for, and a screen reader says
        # nothing about either: the window title changes, which it reads on
        # focus, long after the fact.
        # Except during startup, where the launch cue has already announced this
        # same moment. Two sounds arriving together read as one muddled noise --
        # reported exactly that way -- and the fix is not a pause between them:
        # they are one event announced twice. Starting up *is* getting a
        # document. Nobody opened it.
        if not getattr(app, "starting_up", False):
            self._cue(
                SoundEvent.DOCUMENT_OPENED if path is not None else SoundEvent.DOCUMENT_CREATED
            )
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
            # Every edit invalidates the counts, so every edit marks the bar
            # stale -- and _set_modified cannot do it, because it returns early
            # once the document is already dirty. That left the second edit
            # onwards refreshing the bar only if a key-up happened to follow,
            # which a menu command or a context-menu paste never provides: the
            # word count and the Selection cell simply stopped moving. The touch
            # is coalesced on a timer, so this costs nothing per keystroke.
            self._touch_status()
            # Typing into a selection you are still extending replaces it, so
            # there is nothing left to extend and the anchor points into text
            # that has shifted. Ended here rather than from a key code because
            # a paste and a menu command change the text too, and only one of
            # the three is a keystroke.
            self.text_changed_while_extending()
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
        # The error tone, not merely the box. A modal is announced by the
        # reader when it takes focus, but the *kind* of thing that has happened
        # is exactly what a tone says faster than a title can.
        self._cue(SoundEvent.ERROR)
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

    def _action(self, event: str, message: str) -> None:
        """Report an action that landed, however the user asked to be told.

        The pair of an earcon and a phrase for the *same* moment -- a copy, a
        paste, a started selection. Which of them actually happens is
        ``settings.action_feedback``, resolved in
        :func:`quill.core.action_feedback.resolve` against whether this event has
        a sound in the loaded pack at all: a mode that asked for a tone and found
        none falls through to the words rather than to silence.

        The status bar is written in every mode, silent included. It is not
        feedback, it is the record -- the place somebody reads back with their
        reader to find out what just happened, and a mode about *audio* has no
        business emptying it.
        """
        from quill.core.action_feedback import resolve

        play, speak = resolve(
            getattr(self.app.settings, "action_feedback", "sound"),
            has_sound=self._has_sound_for(event),
        )
        if play:
            self._cue(event)
        if speak:
            self.app.voice.speak(message)
        self._set_status_message(message)

    def _has_sound_for(self, event: str) -> bool:
        """Whether the loaded pack could actually play *event*.

        One method rather than an import at each site, because every feedback mode
        has to ask the same question and answer it the same way: a mode that chose
        a tone for a moment with no clip must fall through to words, never to
        silence. Never raises -- a missing sound stack answers "no".
        """
        try:
            from quill.ui.sound_manager import has_sound_for

            return has_sound_for(event)
        except Exception:  # noqa: BLE001 - no sound stack is an answer, not an error
            return False

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
        # After the veto check and before anything is torn down: a window the
        # user backed out of closing must not have written its state away, and
        # a destroyed control has no cursor position left to read.
        self.remember_document_memory()
        self.stop_timers()
        self._discard_slot()
        # Before Destroy, which takes the window and everything on it: a cue
        # posted after that has no frame left to have come from.
        self._cue(SoundEvent.DOCUMENT_CLOSED)
        self.app.forget_frame(self)
        self.Destroy()

    # ------------------------------------------------------------------ #
