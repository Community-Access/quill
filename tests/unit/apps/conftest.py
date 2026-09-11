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
        #: ``(offset, level, text)`` rows the heading list and Alt+Down report.
        self.heading_rows: list[tuple[int, int, str]] = []
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
        """``(offset, level, text)`` rows, as the real editor reports them.

        Settable by a test (``editor.heading_rows = [...]``) because the rich
        heading ladder is a font size in a Rich Edit control, and there is
        nothing for a stand-in to compute it from.
        """
        return list(self.heading_rows)

    def next_heading(self, position: int, *, reverse: bool = False) -> tuple[int, int] | None:
        """``(offset, level)`` for the next heading past *position*, or ``None``.

        The signature matters. This used to take ``forward=`` and return ``-1``,
        and the real editor takes ``reverse=`` and returns ``None`` -- so
        ``_navigate_heading`` unpacked an int and the stand-in could never have
        caught it. Match wx-side reality, including the shape of "nothing".
        """
        rows = sorted(self.heading_rows)
        if reverse:
            earlier = [row for row in rows if row[0] < position]
            return (earlier[-1][0], earlier[-1][1]) if earlier else None
        later = [row for row in rows if row[0] > position]
        return (later[0][0], later[0][1]) if later else None

    def paragraph_text_at(self, position: int) -> str:
        for offset, _level, text in self.heading_rows:
            if offset == position:
                return text
        return ""

    def caret_format_description(self) -> str:
        return "Body text"

    def set_document_color(self, colour: Any) -> None:
        self.calls.append(("set_document_color", colour))

    def save_rtf(self, path: str) -> None:
        """Write the document where the real TOM save would.

        The bytes are the plain text rather than RTF, deliberately: what the
        save path is being tested for is the temp-file-then-replace dance and
        the colour being stripped and restored around it, not the markup. A
        real file has to appear, though, or ``os.replace`` fails.
        """
        self.calls.append(("save_rtf", path))
        from pathlib import Path as _Path

        _Path(path).write_text(self.control.GetValue(), encoding="utf-8")

    def set_background_color(self, colour: Any) -> None:
        self.calls.append(("set_background_color", colour))

    def set_word_wrap(self, on: bool) -> None:
        self.calls.append(("set_word_wrap", on))


class FakeTimer:
    """``wx.Timer``, counted rather than run. Autosave in a test would put a
    real file write on a real clock in the middle of an assertion."""

    def __init__(self) -> None:
        self.started: list[int] = []
        self.stopped = 0

    def Start(self, milliseconds: int) -> None:  # noqa: N802 - wx API shape
        self.started.append(int(milliseconds))

    def Stop(self) -> None:  # noqa: N802 - wx API shape
        self.stopped += 1


class FakePageData:
    """Stands in for ``wx.PageSetupDialogData`` and ``wx.PrintData`` alike.

    Both are opaque C++ value objects that only accept each other, so a bare
    ``object()`` is rejected by the first real wx call the command makes. This
    carries the two methods Page Setup uses and is otherwise an identity: what
    the tests ask is whether an OK *replaced* the stored value and a cancel
    *left it alone*.
    """

    def __init__(self, label: str = "") -> None:
        self.label = label
        self.print_data: Any = None

    def SetPrintData(self, data: Any) -> None:  # noqa: N802 - wx API shape
        self.print_data = data

    def GetPrintData(self) -> Any:  # noqa: N802 - wx API shape
        return self.print_data


class FakePrintSettings:
    """``app.print_settings``: page setup and printer data, shared app-wide.

    The real objects are ``wx.PageSetupDialogData`` and ``wx.PrintData``, which
    a test has no way to inspect meaningfully. What the commands actually do
    with them is *replace* them after an OK and *leave them alone* after a
    cancel, and that is what these placeholders let a test assert.
    """

    def __init__(self) -> None:
        self.page_setup: Any = FakePageData("page setup")
        self.print_data: Any = FakePageData("print data")


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
        self.saved_keymaps: list[Any] = []
        self.saved_features = 0
        self.reloaded_abbreviations = 0
        #: Page setup and printer data, shared by every document in the real
        #: app. Only identity matters here -- the commands read it, hand it to
        #: wx and write it back -- so a bare object is the honest stand-in.
        self.print_settings = FakePrintSettings()

    def command_registry(self, _frame: Any) -> list[Any]:
        """What the palette and Go To Anything are built from. Empty is fine:
        both are being tested for *what they do with the answer*, not for the
        contents of a list they are handed."""
        return []

    def save_keymap(self) -> None:
        self.saved_keymaps.append(dict(self.keymap))

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
        self.saved_features += 1

    def reload_abbreviations(self) -> None:
        self.reloaded_abbreviations += 1

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


@pytest.fixture(scope="session")
def wx_app():
    """One ``wx.App`` for the session.

    Almost nothing here needs it -- the whole point of the harness is that the
    commands run without wx -- but ``wx.Printout`` refuses to be constructed
    without an App, and printing is worth reaching rather than stubbing past.
    Session-scoped because a second App in one process is not supported.
    """
    app = wx.App()
    yield app
    app.Destroy()


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
    from quill.apps.lite_keymap_editor import DocumentKeymapMixin
    from quill.apps.lite_printing import DocumentPrintMixin
    from quill.apps.lite_window_clipboard import DocumentClipboardMixin
    from quill.apps.lite_window_commands import DocumentCommandsMixin
    from quill.apps.lite_window_context_menu import DocumentContextMenuMixin
    from quill.apps.lite_window_file import DocumentFileMixin
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
        DocumentFileMixin,
        # Printing and the Keyboard Manager, added 2026-09-11. Both are one
        # state change behind a wx dialog, which is the shape the dialog
        # recorder (``lite_dialogs``) exists to make testable.
        DocumentPrintMixin,
        DocumentKeymapMixin,
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
            # ``newline``, not ``line_ending``: that is the attribute name the
            # real DocumentFrame uses and the one cmd_file_format reads. The
            # stub carried the other spelling and nothing noticed, because no
            # test had reached the command that reads it.
            self.newline = chr(13) + chr(10)
            self.line_ending = self.newline
            self.failures: list[tuple[str, str]] = []
            self.printed: list[str] = []
            # The recovery slot and the autosave timer, set up in
            # DocumentFrame.__init__ and read by save() on every write. A window
            # that never had a slot is the ordinary case -- one is created the
            # first time unsaved work is copied aside -- so None is the honest
            # starting value rather than a stub object.
            self._slot = None
            self._autosave = FakeTimer()
            self.colour_calls: list[Any] = []
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
            #: The modeless Find window, kept so a second Ctrl+F raises the one
            #: already open instead of stacking another over the same document.
            self._find_dialog = None
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

        def _set_mode_internal(self, mode: str) -> None:
            """Swap the editor surface without reloading the text.

            The real one on DocumentAppearanceMixin destroys and rebuilds a wx
            control; what callers depend on is only that ``editor.mode`` has
            moved by the time it returns.
            """
            self.editor.set_text_mode(mode)

        def apply_theme(self) -> None:
            self.colour_calls.append("theme")

        def _set_whole_document_colour(self, rgb: Any) -> None:
            """Recorded. The real one lives on DocumentAppearanceMixin and needs
            wx colours; what matters here is that a save strips the theme colour
            and puts it back, so a dark-mode save cannot leak light grey text
            into somebody's file."""
            self.colour_calls.append(rgb)

        def _apply_rich_theme_colour(self) -> None:
            self.colour_calls.append("restored")

        def _report_failure(self, caption: str, message: str) -> None:
            """Recorded, not raised. A failed print or save is announced to the
            user and must not take the command down with it."""
            self.failures.append((caption, message))

        def document_name(self) -> str:
            return self.path.name if self.path else "Untitled 1"

        # No ``_printable_lines`` / ``_heading_marks`` here on purpose: the real
        # ones in DocumentPrintMixin work against these fakes, and shadowing
        # them would test the stand-in instead of the heading marking that is
        # the only interesting thing printing does to a document.

        def _print_font(self) -> Any:
            """The real one asks wx for a font. Printing itself is stubbed."""
            return None

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


# --------------------------------------------------------------------------- #
# Dialogs
# --------------------------------------------------------------------------- #


class DialogRecorder:
    """Every window QuillLite can open, replaced by a record-and-answer stub.

    Twenty-odd commands are *one state change behind a modal dialog*: choose a
    file, choose a font, choose a slot, then do the thing. Without a seam they
    stay shape-only forever, and shape-only is what let F8 ship broken -- so the
    seam is worth building rather than accepting the gap.

    Two rules, and they are the same two the rest of this harness follows.

    **Answer, do not simulate.** Nothing here draws a dialog or decides what a
    user would pick. A test says what came back (``dialogs.answer("FileDialog",
    path)``) and asserts what the command did with it. The default answer is
    **cancel**, because cancel is the case that is forgotten: a command that
    quietly acts on a cancelled dialog is the bug this catches.

    **Patch where the name is looked up.** A dialog imported at module scope
    has to be replaced in the module that imported it, not where it is defined
    -- ``lite_window_commands.choose_heading`` is a different binding from
    ``lite_dialogs.choose_heading``, and patching the second leaves the first
    untouched. The table below names both ends for that reason.
    """

    #: ``(module path, attribute)`` for every dialog entry point, keyed by the
    #: short name a test uses. Where a module imported the name at its own
    #: scope, that module is the target -- see the docstring.
    TARGETS: dict[str, tuple[str, str]] = {
        # Imported inside the function that uses them: the defining module is
        # the only binding, so patching it there covers every caller.
        "choose_from_rows": ("quill.apps.lite_dialogs", "choose_from_rows"),
        # Same window, second binding: lite_window_clipboard imports it at
        # module scope, so patching only lite_dialogs left the tray and the clip
        # library opening a real wx.Dialog in the middle of a test.
        "choose_from_rows_clipboard": ("quill.apps.lite_window_clipboard", "choose_from_rows"),
        "edit_spelling_voice": ("quill.apps.lite_spelling_voice_dialog", "edit_spelling_voice"),
        "AppFeaturesDialog": ("quill.ui.app_features_dialog", "AppFeaturesDialog"),
        "CommandPaletteDialog": ("quill.ui.palette", "CommandPaletteDialog"),
        "GoToAnythingDialog": ("quill.ui.palette", "GoToAnythingDialog"),
        "review_textctrl": ("quill.ui.spell_review", "review_textctrl"),
        "show_help": ("quill.ui.app_context_help", "show_help"),
        # Imported at module scope by their caller: patch the caller.
        "show_text_window": ("quill.apps.lite_window_commands", "show_text_window"),
        "show_text_window_marks": ("quill.apps.lite_window_marks", "show_text_window"),
        "choose_heading": ("quill.apps.lite_window_commands", "choose_heading"),
        "ask_line_number": ("quill.apps.lite_window_commands", "ask_line_number"),
        "edit_file_format": ("quill.apps.lite_window_tools", "edit_file_format"),
        "edit_preferences": ("quill.apps.lite_window_view", "edit_preferences"),
        "FindDialog": ("quill.apps.lite_window_find", "FindDialog"),
        "ReplaceDialog": ("quill.apps.lite_window_find", "ReplaceDialog"),
        "KeymapEditorDialog": ("quill.apps.lite_keymap_editor", "KeymapEditorDialog"),
    }

    #: The sentinel meaning "no test set an answer, so answer cancel".
    CANCELLED = object()

    def __init__(self, monkeypatch: Any) -> None:
        self._monkeypatch = monkeypatch
        self.answers: dict[str, Any] = {}
        #: ``(name, args, kwargs)`` in the order the commands opened them.
        self.opened: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        for name in self.TARGETS:
            self._install(name)

    # -- the seam --------------------------------------------------------- #

    def _install(self, name: str) -> None:
        import importlib

        module_path, attribute = self.TARGETS[name]
        module = importlib.import_module(module_path)
        if not hasattr(module, attribute):  # pragma: no cover - a renamed dialog
            raise AssertionError(
                f"{module_path}.{attribute} does not exist. The recorder's table is "
                "stale, which would leave a real dialog opening in a test run."
            )
        self._monkeypatch.setattr(module, attribute, self._stub(name))

    def _stub(self, name: str) -> Any:
        def opened(*args: Any, **kwargs: Any) -> Any:
            self.opened.append((name, args, kwargs))
            answer = self.answers.get(name, self.CANCELLED)
            return None if answer is self.CANCELLED else answer

        return opened

    # -- what a test says -------------------------------------------------- #

    #: Names that are two bindings on one window. A test says the short name and
    #: gets both, because which module imported the dialog is the recorder's
    #: problem rather than the test author's.
    ALIASES: dict[str, tuple[str, ...]] = {
        "choose_from_rows": ("choose_from_rows", "choose_from_rows_clipboard"),
        "show_text_window": ("show_text_window", "show_text_window_marks"),
    }

    def answer(self, name: str, value: Any) -> None:
        """Make *name* return *value* instead of cancelling."""
        if name not in self.TARGETS:  # pragma: no cover - a typo in a test
            raise AssertionError(f"{name!r} is not a dialog this recorder patches")
        for alias in self.ALIASES.get(name, (name,)):
            self.answers[alias] = value

    def names(self) -> list[str]:
        return [name for name, _args, _kwargs in self.opened]

    def kwargs_for(self, name: str) -> dict[str, Any]:
        """The keyword arguments the last opening of *name* was given."""
        wanted = self.ALIASES.get(name, (name,))
        for opened, _args, kwargs in reversed(self.opened):
            if opened in wanted:
                return kwargs
        raise AssertionError(f"{name} was never opened; opened: {self.names()}")

    def args_for(self, name: str) -> tuple[Any, ...]:
        wanted = self.ALIASES.get(name, (name,))
        for opened, args, _kwargs in reversed(self.opened):
            if opened in wanted:
                return args
        raise AssertionError(f"{name} was never opened; opened: {self.names()}")


class FakeModalDialog:
    """A wx dialog class used as ``with wx.FileDialog(...) as d`` or plain.

    Built by :func:`_fake_dialog_class` with the answers baked in, because the
    commands construct these themselves -- there is no seam to hand an instance
    through, only the class name on the ``wx`` module.
    """

    _answer_id: Any = None
    _values: dict[str, Any] = {}
    constructed: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).constructed.append((args, kwargs))

    def __enter__(self) -> FakeModalDialog:
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False

    def ShowModal(self) -> Any:  # noqa: N802 - wx API shape
        return self._answer_id

    def Destroy(self) -> None:  # noqa: N802 - wx API shape
        return None

    def __getattr__(self, name: str) -> Any:
        """Answer GetPath / GetPaths / GetFontData / ... from the baked values.

        A dialog method a test did not name raises rather than returning a
        silent ``None``: a command reading a value nobody supplied should fail
        loudly in the test rather than take the default branch by accident.
        """
        if name in self._values:
            value = self._values[name]
            return (lambda *_a, **_k: value) if not callable(value) else value
        raise AttributeError(
            f"{name} was not supplied to this fake dialog; add it to the values dict"
        )


def _fake_dialog_class(answer_id: Any, **values: Any) -> type[FakeModalDialog]:
    """A one-off dialog class answering *answer_id* and the named getters."""
    return type(
        "FakeDialog",
        (FakeModalDialog,),
        {"_answer_id": answer_id, "_values": values, "constructed": []},
    )


@pytest.fixture
def lite_dialogs(monkeypatch):
    """Every QuillLite dialog, recorded and answered. See :class:`DialogRecorder`."""
    return DialogRecorder(monkeypatch)


@pytest.fixture
def fake_wx_dialog(monkeypatch):
    """Replace a ``wx`` dialog class (``FileDialog``, ``FontDialog``, ...).

    Returns ``install(name, answer_id, **getters)`` and hands back the class, so
    a test can assert on how it was constructed as well as what the command did
    with the answer.
    """

    def install(name: str, answer_id: Any, **getters: Any) -> type[FakeModalDialog]:
        cls = _fake_dialog_class(answer_id, **getters)
        monkeypatch.setattr(wx, name, cls)
        return cls

    return install
