"""A QuillLite document window with the wx taken out, for testing behaviour.

Every command in QuillLite is a method on a mixin that reads and writes a text
control and then says what it did. Both halves matter and only one of them was
being checked: the command table had gates for its keys, its mnemonics and its
labels, and the *behaviour* of the commands was left to a person listening to a
running build.

That is how F8 shipped broken. ``cmd_start_selection`` was correct, the key was
correct, the menu was correct -- and a key-up handler wired to the same control
threw the anchor away a millisecond later, so F8 followed by Shift+F8 answered
"No selection in progress" every single time. No table gate can see that: it is
an interaction between a command and an event hook, and the only thing that
catches it is calling both, in order, the way the window does.

So this is the window, minus wx: a text model that behaves like ``wx.TextCtrl``
(including the parts that surprise people -- see :meth:`FakeControl.GetInsertionPoint`),
a rich-text editor stand-in, an app stand-in, and a class with the real mixins
composed onto it. The commands under test are the real ones; nothing here
reimplements a command or asserts against a copy of its logic.

Two rules for anything added here:

* **Match wx where wx is odd, not where it is convenient.** ``GetInsertionPoint``
  returning the *start* of a selection is a real wxMSW behaviour that a stand-in
  which returned "the caret" would hide, and code written against the convenient
  version is code that fails on the user's machine.
* **Record, never suppress.** Announcements, earcons and status touches all land
  in lists. A command whose only output is a sentence is a command whose only
  testable output is that sentence.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx


class _SkippableEvent:
    """Enough of ``wx.CommandEvent`` for a cue handler: it calls ``Skip``."""

    def __init__(self) -> None:
        self.skipped = False

    def Skip(self, skip: bool = True) -> None:  # noqa: N802 - wx API shape
        self.skipped = bool(skip)


#: wx event type ids for the three clipboard events, so a recorded binding can be
#: matched back to the operation it reports.
_CLIPBOARD_EVENT_KINDS = {
    wx.EVT_TEXT_CUT.typeId: "cut",
    wx.EVT_TEXT_COPY.typeId: "copy",
    wx.EVT_TEXT_PASTE.typeId: "paste",
}


class FakeControl:
    """The slice of ``wx.TextCtrl`` QuillLite's commands actually use.

    Text, a selection, an insertion point and a small undo stack. Line
    arithmetic is computed from the text rather than stored, so a command that
    edits the text cannot leave the line map stale -- which is the class of bug
    the real control cannot have and a lazier stand-in would invent.
    """

    def __init__(self, text: str = "", cursor: int = 0) -> None:
        self._text = text
        self._cursor = min(cursor, len(text))
        self._sel: tuple[int, int] = (self._cursor, self._cursor)
        self._undo: list[tuple[str, int]] = []
        self._redo: list[tuple[str, int]] = []
        self.clipboard = ""
        self.shown_positions: list[int] = []
        self.focused = False
        self.refreshed = 0
        self.font: Any = None
        self.colours: dict[str, Any] = {}
        self.clipboard_handlers: dict[str, Any] = {}

    # -- text ---------------------------------------------------------- #

    def GetValue(self) -> str:
        return self._text

    def SetValue(self, text: str) -> None:
        self._push_undo()
        self._text = text
        self._clamp()

    def ChangeValue(self, text: str) -> None:
        """As wx: set the text *without* an undo step or a text event."""
        self._text = text
        self._clamp()

    def GetLastPosition(self) -> int:
        return len(self._text)

    def Replace(self, start: int, end: int, text: str) -> None:
        self._push_undo()
        self._text = self._text[:start] + text + self._text[end:]
        self._cursor = start + len(text)
        self._sel = (self._cursor, self._cursor)
        self._clamp()

    def Remove(self, start: int, end: int) -> None:
        self.Replace(start, end, "")

    def WriteText(self, text: str) -> None:
        start, end = self._sel
        if end > start:
            self.Replace(start, end, text)
            return
        self.Replace(self._cursor, self._cursor, text)

    # -- caret and selection ------------------------------------------- #

    def GetInsertionPoint(self) -> int:
        """As wxMSW: the *start* of the selection whenever there is one.

        Not a shortcut -- this is what the real control answers, and it is why
        extend mode cannot simply ask "where is the caret" after it has set a
        selection. A stand-in that returned the moving end would make broken
        code pass.
        """
        start, end = self._sel
        return start if end > start else self._cursor

    def SetInsertionPoint(self, position: int) -> None:
        self._cursor = max(0, min(int(position), len(self._text)))
        self._sel = (self._cursor, self._cursor)

    def GetSelection(self) -> tuple[int, int]:
        return self._sel

    def SetSelection(self, start: int, end: int) -> None:
        low, high = sorted((int(start), int(end)))
        low = max(0, min(low, len(self._text)))
        high = max(0, min(high, len(self._text)))
        self._sel = (low, high)
        self._cursor = high

    def SelectAll(self) -> None:
        self.SetSelection(0, len(self._text))

    def ShowPosition(self, position: int) -> None:
        self.shown_positions.append(int(position))

    def SetFocus(self) -> None:
        self.focused = True

    def Refresh(self) -> None:
        self.refreshed += 1

    # -- lines --------------------------------------------------------- #

    def GetNumberOfLines(self) -> int:
        return self._text.count("\n") + 1

    def PositionToXY(self, position: int) -> tuple[bool, int, int]:
        position = max(0, min(int(position), len(self._text)))
        before = self._text[:position]
        line = before.count("\n")
        column = position - (before.rfind("\n") + 1)
        return (True, column, line)

    def XYToPosition(self, column: int, line: int) -> int:
        lines = self._text.split("\n")
        if line < 0 or line >= len(lines):
            return -1
        start = sum(len(text) + 1 for text in lines[:line])
        return start + min(int(column), len(lines[line]))

    # -- clipboard ----------------------------------------------------- #

    def Cut(self) -> None:
        start, end = self._sel
        if end > start:
            self.clipboard = self._text[start:end]
            self.Remove(start, end)
        self._raise_clipboard_event("cut")

    def Copy(self) -> None:
        start, end = self._sel
        if end > start:
            self.clipboard = self._text[start:end]
        self._raise_clipboard_event("copy")

    def Paste(self) -> None:
        if self.clipboard:
            self.WriteText(self.clipboard)
        self._raise_clipboard_event("paste")

    def _raise_clipboard_event(self, kind: str) -> None:
        """Fire the handler wx would fire, because the cue now hangs off it.

        ``wxEVT_TEXT_CUT`` / ``COPY`` / ``PASTE`` are raised by the real control
        from the Windows messages it acts on, which is *why* QuillLite's feedback
        was moved onto them: they fire once whether the command came from the
        accelerator, the menu, the context menu, or the control's own key
        handling. A stand-in that stayed silent would let the cue be deleted with
        every test still green.
        """
        handler = self.clipboard_handlers.get(kind)
        if handler is not None:
            handler(_SkippableEvent())

    def CanPaste(self) -> bool:
        return bool(self.clipboard)

    # -- undo ---------------------------------------------------------- #

    def _push_undo(self) -> None:
        self._undo.append((self._text, self._cursor))
        self._redo.clear()

    def CanUndo(self) -> bool:
        return bool(self._undo)

    def CanRedo(self) -> bool:
        return bool(self._redo)

    def Undo(self) -> None:
        if not self._undo:
            return
        self._redo.append((self._text, self._cursor))
        self._text, self._cursor = self._undo.pop()
        self._clamp()

    def Redo(self) -> None:
        if not self._redo:
            return
        self._undo.append((self._text, self._cursor))
        self._text, self._cursor = self._redo.pop()
        self._clamp()

    # -- appearance ---------------------------------------------------- #

    def SetFont(self, font: Any) -> None:
        self.font = font

    def SetBackgroundColour(self, colour: Any) -> None:
        self.colours["background"] = colour

    def SetForegroundColour(self, colour: Any) -> None:
        self.colours["foreground"] = colour

    def Bind(self, event: Any, handler: Any, *_args: Any, **_kwargs: Any) -> None:
        """Record the clipboard bindings; ignore the rest.

        Only three bindings carry behaviour a command test can observe, and they
        are the three the real window puts here in ``bind_clipboard_cues``.
        """
        kind = _CLIPBOARD_EVENT_KINDS.get(getattr(event, "typeId", None))
        if kind is not None:
            self.clipboard_handlers[kind] = handler

    def _clamp(self) -> None:
        self._cursor = max(0, min(self._cursor, len(self._text)))
        low, high = self._sel
        low = max(0, min(low, len(self._text)))
        high = max(0, min(high, len(self._text)))
        self._sel = (low, high) if high > low else (self._cursor, self._cursor)


class FakeEditor:
    """The rich-text surface, recording what was asked of it.

    Formatting is a request to a Rich Edit control and there is nothing to read
    back, so what is testable is *that the right request was made with the right
    argument*, plus the announcement that followed. Both are recorded.
    """

    def __init__(self, control: FakeControl, mode: str = "plain") -> None:
        self.control = control
        self.mode = mode
        self.rtf: bool = True
        self.calls: list[tuple[str, Any]] = []
        self.attrs: dict[str, bool] = {}
        self.font_size = 11
        self.zoom = 100
        self.headings: dict[int, int] = {}
        self.bullets = False

    def rtf_available(self) -> bool:
        return self.rtf

    def toggle_overtype(self) -> bool:
        self.overtype = not getattr(self, "overtype", False)
        return self.overtype

    def toggle_font_attr(self, attr: str) -> bool:
        self.attrs[attr] = not self.attrs.get(attr, False)
        self.calls.append(("toggle_font_attr", attr))
        return self.attrs[attr]

    def set_alignment(self, alignment: str) -> bool:
        self.calls.append(("set_alignment", alignment))
        return True

    def set_line_spacing(self, spacing: float) -> bool:
        self.calls.append(("set_line_spacing", spacing))
        return True

    def set_bullets(self, on: bool) -> bool:
        self.bullets = on
        self.calls.append(("set_bullets", on))
        return True

    def bullets_at_caret(self) -> bool:
        return self.bullets

    def set_font_name(self, name: str) -> bool:
        self.calls.append(("set_font_name", name))
        return True

    def set_font_size(self, size: int) -> bool:
        self.font_size = size
        self.calls.append(("set_font_size", size))
        return True

    def step_font_size(self, *, larger: bool) -> float:
        self.font_size = max(1, self.font_size + (2 if larger else -2))
        self.calls.append(("step_font_size", larger))
        return float(self.font_size)

    def set_zoom(self, numerator: float, denominator: float) -> None:
        self.zoom = (numerator, denominator)
        self.calls.append(("set_zoom", (numerator, denominator)))

    def set_text_mode(self, mode: str) -> None:
        self.mode = mode
        self.calls.append(("set_text_mode", mode))

    def set_heading(self, level: int) -> bool:
        self.calls.append(("set_heading", level))
        return True

    def heading_level_at_caret(self) -> int:
        return self.headings.get(self.control.GetInsertionPoint(), 0)

    def all_headings(self) -> list[tuple[int, int, str]]:
        return []

    def next_heading(self, _position: int, *, forward: bool = True) -> int:
        return -1

    def paragraph_text_at(self, _position: int) -> str:
        return ""

    def caret_format_description(self) -> str:
        return "Body text"

    def set_document_color(self, colour: Any) -> None:
        self.calls.append(("set_document_color", colour))

    def set_background_color(self, colour: Any) -> None:
        self.calls.append(("set_background_color", colour))

    def set_word_wrap(self, on: bool) -> None:
        self.calls.append(("set_word_wrap", on))


class FakeVoice:
    def __init__(self) -> None:
        self.said: list[str] = []

    def speak(self, message: str) -> None:
        self.said.append(message)


class FakeApp:
    """The application object, with only what a document window reaches for."""

    def __init__(self, tmp_path: Any, settings: Any) -> None:
        from quill.core.clip_library import ClipLibrary
        from quill.core.copy_tray import CopyTray

        self.settings = settings
        self.data_dir = tmp_path
        self.voice = FakeVoice()
        self.frames: list[Any] = []
        self.starting_up = False
        self.saved_settings = 0
        self.reapplied = 0
        self.rebuilt_menus = 0
        self.exited = 0
        self.cycled: list[bool] = []
        self.opened: list[Any] = []
        # The real stores, in a temporary directory. A stand-in for CopyTray
        # would be a second implementation of numbered slots to keep in step with
        # the first, and the commands under test are mostly *about* the store.
        self.copy_tray = CopyTray(tmp_path)
        self.clip_library = ClipLibrary(tmp_path)
        self.collected = ""
        self.abbreviations: dict[str, str] = {}
        self.features: dict[str, bool] = {}
        self.keymap: dict[str, str] = {}
        self.document_memory = None

    def feature_enabled(self, _area: str) -> bool:
        return True

    def save_settings(self) -> None:
        self.saved_settings += 1

    def reapply_settings(self) -> None:
        self.reapplied += 1

    def rebuild_all_menus(self) -> None:
        self.rebuilt_menus += 1

    def refresh_all_menus(self) -> None:
        self.rebuilt_menus += 1

    def save_features(self) -> None:
        return None

    def reload_abbreviations(self) -> None:
        return None

    def save_abbreviations(self) -> None:
        return None

    def cycle(self, *args: Any, **kwargs: Any) -> None:
        self.cycled.append(args[-1] if args else kwargs.get("forward", True))

    def exit_all(self) -> None:
        self.exited += 1

    def new_window(self, *args: Any, **kwargs: Any) -> Any:
        self.opened.append((args, kwargs))
        return None

    def open_path(self, *args: Any, **kwargs: Any) -> Any:
        self.opened.append((args, kwargs))
        return None

    def focus_frame(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def binding_for(self, _command: str) -> str:
        return ""


@pytest.fixture
def lite_settings():
    """Real :class:`Settings`, so a test reads the same defaults the app does.

    QuillLite's own, not QUILL's. This was QUILL's until 2026-09-10, which
    happened to work while the tests only touched fields both objects have --
    and stopped the moment a View-menu test reached for ``show_status_bar``,
    which is one of seventeen fields only the small editor has. A stand-in built
    on the wrong settings class is a stand-in that can pass while the app cannot
    run, so it is the app's class or nothing.
    """
    from quill.core.lite.settings import Settings

    return Settings()


@pytest.fixture
def lite_window(tmp_path, lite_settings):
    """Factory: ``lite_window("text", cursor=3)`` -> a window with real commands.

    The mixins are the shipped ones. What is faked is everything below them.
    """
    from quill.apps.lite_window_clipboard import DocumentClipboardMixin
    from quill.apps.lite_window_commands import DocumentCommandsMixin
    from quill.apps.lite_window_context_menu import DocumentContextMenuMixin
    from quill.apps.lite_window_format import DocumentFormatCommandsMixin
    from quill.apps.lite_window_history import DocumentHistoryMixin
    from quill.apps.lite_window_lines import DocumentLineMixin
    from quill.apps.lite_window_marks import DocumentMarksMixin
    from quill.apps.lite_window_selection import DocumentSelectionMixin
    from quill.apps.lite_window_spelling import DocumentSpellingMixin
    from quill.apps.lite_window_tools import DocumentToolsMixin
    from quill.apps.lite_window_typing import DocumentTypingMixin
    from quill.apps.lite_window_view import DocumentViewCommandsMixin

    class LiteWindowStub(
        DocumentSelectionMixin,
        DocumentMarksMixin,
        DocumentLineMixin,
        DocumentToolsMixin,
        DocumentClipboardMixin,
        DocumentFormatCommandsMixin,
        DocumentHistoryMixin,
        DocumentTypingMixin,
        # The View menu and the Spelling menu, added 2026-09-10. Both are the
        # same shape as the ones already here -- a state change plus a sentence --
        # and both were shape-only until the coverage ratchet
        # (quill.tools.lite_command_coverage) made that visible. The context-menu
        # mixin comes with them for its ``spell_ignores`` list, which the
        # spelling navigation consults on every hop.
        DocumentViewCommandsMixin,
        DocumentSpellingMixin,
        DocumentContextMenuMixin,
        DocumentCommandsMixin,
    ):
        """A document window with wx removed and every output recorded."""

        def __init__(self, text: str, cursor: int, mode: str) -> None:
            self.control = FakeControl(text, cursor)
            self.editor = FakeEditor(self.control, mode)
            self.app = FakeApp(tmp_path, lite_settings)
            self.app.frames.append(self)
            self.announcements: list[str] = []
            self.cues: list[str] = []
            self.actions: list[tuple[str, str]] = []
            self.status_touches = 0
            self.status_messages: list[str] = []
            self.modified = False
            self.checks_synced = 0
            self.path = None
            self.number = 1
            self.closed = 0
            self.encoding = "utf-8"
            self.line_ending = chr(13) + chr(10)
            self.popped_menus: list[Any] = []
            # The same state ``DocumentFrame.__init__`` sets up, set up the same
            # way. Anything a command reads must exist before the command runs,
            # and the real window's ordering is part of what is being tested.
            from quill.core.locations import LocationRing
            from quill.core.numbered_bookmarks import BookmarkSet

            self.bookmarks = BookmarkSet()
            self.locations = LocationRing()
            self._tracked_length = len(text)
            self._loading = False
            self._find_options: dict[str, Any] = {}
            self.status_bar_focused = 0
            self._init_selection()
            self._init_overwrite()
            self._init_spelling()
            self._init_context_menu()
            # The window binds these in __init__ too, and the cue for cut, copy
            # and paste now hangs off them: a stub that skipped the binding would
            # report all three as silent and be believed.
            self.bind_clipboard_cues()

        # -- the recorded outputs ------------------------------------- #

        def _announce(self, message: str) -> None:
            self.announcements.append(message)
            self.app.voice.speak(message)
            self.status_messages.append(message)

        def _cue(self, event: str) -> None:
            self.cues.append(str(event))

        def _action(self, event: str, message: str) -> None:
            """The real resolver, over the fake channels.

            The rule under test is which of the two channels fires, so the rule
            itself is imported rather than restated: a copy here could agree with
            a bug.
            """
            from quill.core.action_feedback import resolve

            self.actions.append((str(event), message))
            play, speak = resolve(
                self.app.settings.action_feedback,
                has_sound=self._has_sound_for(event),
            )
            if play:
                self._cue(event)
            if speak:
                self.app.voice.speak(message)
            self.status_messages.append(message)

        #: Events the "loaded pack" has a clip for. Set by the factory to the ones
        #: the shipped Ink pack actually ships; a test that wants the no-clip
        #: fall-through empties it.
        available_sounds: frozenset[str] | set[str] = frozenset()

        def _has_sound_for(self, event: str) -> bool:
            """The seam the real window resolves against ``sound_manager``.

            Faked rather than reached through, because the answer in the real app
            depends on which pack is loaded and on there being an audio stack at
            all -- neither of which a command test should be deciding.
            """
            return str(event) in self.available_sounds

        # -- the system clipboard, kept out of the tests ---------------- #

        def _clipboard_text(self) -> str:
            """The fake control's clipboard, not the machine's.

            ``wx.TheClipboard`` is a shared, single-owner OS resource: a test that
            read it would race the user's own clipboard, the screen reader's
            polling and every other test in the suite, and would have to be
            marked ``machine_global`` for its trouble. The commands under test
            care about what came back, not where from.
            """
            return self.control.clipboard

        def _set_clipboard_text(self, text: str) -> bool:
            self.control.clipboard = text
            return True

        def _set_status_message(self, message: str) -> None:
            self.status_messages.append(message)

        def _touch_status(self) -> None:
            self.status_touches += 1

        def _set_modified(self, value: bool) -> None:
            self.modified = value

        def _sync_check_items(self) -> None:
            self.checks_synced += 1

        def _update_title(self) -> None:
            return None

        def Close(self, force: bool = False) -> bool:  # noqa: N802 - wx API shape
            self.closed += 1
            return True

        def switch_mode(self, mode: str) -> None:
            """What ``DocumentFrame.switch_mode`` does, minus the reload."""
            self.editor.set_text_mode(mode)
            self._announce(
                "Rich text mode" if mode == "rich" else "Plain text mode",
            )

        def describe_indent_at_cursor(self) -> str:
            return "no indent"

        def focus_status_bar(self) -> None:
            """Where F6 goes. Recorded rather than performed: the bar is wx.

            What the command decides is *whether* to go there -- a hidden bar
            has nowhere to move to -- and that decision is the testable half.
            """
            self.status_bar_focused += 1

        # -- the window's own event hooks, as the real window wires them -- #

        def on_caret_moved(self, key_code: int) -> None:
            """What ``EVT_KEY_UP`` does, in the order ``lite_window`` does it.

            The reason this stub exists: the F8 bug lived *between* a command and
            this hook, so a test that only calls commands cannot see it.
            """
            self._touch_status()
            self.extend_selection_after_move(key_code)

        def on_text_changed(self) -> None:
            """What ``EVT_TEXT`` does, in the order ``lite_window`` does it."""
            self._set_modified(True)
            self._touch_status()
            self.text_changed_while_extending()

    def make(text: str = "", cursor: int = 0, mode: str = "plain") -> Any:
        window = LiteWindowStub(text, cursor, mode)
        window.available_sounds = frozenset({
            "search_not_found",
            "search_found",
            "search_wrapped",
            "text_cut",
            "text_copied",
            "text_pasted",
            "text_deleted",
            "undo_performed",
            "redo_performed",
            "selection_started",
            "selection_completed",
        })
        return window

    return make
