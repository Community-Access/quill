"""Review Dictation: the window dictated words wait in before they are inserted.

D-2 of the 2026-10-13 dictation gap plan, one window for QUILL, QUILL Lite and
QUILL Transcribe. The words are in a **real, editable, multi-line text
control**, so a screen reader reads them by line, word and character and a
braille display shows them; the person may type into it as well as dictate.
Nothing reaches the document, or the other program, until Insert.

* **Keys** (the window's own accelerator table): Insert, Ctrl+Enter; Read It,
  Ctrl+R; What Changed, Ctrl+D; Undo Change, Ctrl+Z (with no AI change to
  undo, it undoes typing in the text, as it would anywhere); Back to What I
  Said, Ctrl+Shift+Z; Discard, Escape, which asks first when the AI has
  changed the words, and cancels a request that is still on its way instead;
  Polish, Ctrl+P, only when "Allow polishing my dictation with AI" is on.
  Close keeps the words for next time (the rescue file) and carries no access
  key (GATE-14).
* **Asking the AI**: type an instruction and press Enter, or say it after the
  command word ("QUILL make it shorter"), or turn on Talk About It and just say
  it. What changed is spoken, two sentences at most, and shown in What Changed.
* **What is said** (GATE-13): nothing on opening -- the title and the focused
  text are what the reader says -- and after that only outcomes the reader
  cannot know: the summary of a change, "Working.", a failure.

:class:`ReviewDesk` is what a host's dictation feedback port returns from
``review()``; the host supplies the ``_review_*`` hooks listed on it. The
words, the requests and every sentence are
:class:`~quill.core.windows_dictation.review_conversation.ReviewConversation`'s.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.windows_dictation.review_conversation import ReviewConversation
from quill.core.windows_dictation.review_session import ReviewSession, load_rescue
from quill.core.windows_dictation.vocabulary import Command
from quill.ui.accessible_names import set_accessible_name
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.dialog_contract import bind_close_button, show_message_box
from quill.ui.dpi import dip_size
from quill.ui.hosted_ai_dialogs import _PAD, _read_only, focus_on, take_focus

__all__ = ["TITLE", "DictationReviewFrame", "ReviewBoxDocument", "ReviewDesk", "defer"]

TITLE = "Review Dictation"

#: How a voice command reaches the window: after the phrase has been handled,
#: never inside it, because the consent question and Discard's question are
#: modal and a modal window inside a recogniser callback holds it open.
defer: Callable[..., Any] = wx.CallAfter


class ReviewBoxDocument:
    """The dictation document port over the review's text control.

    While the review is open the host points its controller here, so what is
    dictated goes into the review, one undo step a phrase, and never through
    keystrokes into another program.
    """

    def __init__(self, control: wx.TextCtrl) -> None:
        self._control = control

    def unavailable_reason(self, *, writing: bool) -> str:
        del writing
        try:
            if not self._control or not self._control.IsEditable():
                return "The review window has closed."
        except RuntimeError:
            return "The review window has closed."
        return ""

    def single_line(self) -> bool:
        return False

    def context(self) -> tuple[str, str]:
        start, end = self._control.GetSelection()
        last = self._control.GetLastPosition()
        return (
            str(self._control.GetRange(max(0, start - 80), start)),
            str(self._control.GetRange(end, min(end + 2, last))),
        )

    def selection(self) -> tuple[int, int]:
        start, end = self._control.GetSelection()
        return int(start), int(end)

    def select(self, start: int, end: int) -> None:
        self._control.SetSelection(start, end)

    def insert(self, text: str) -> tuple[int, int]:
        start, end = self.selection()
        return self.replace(start, end, text)

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        replace_as_one_undo(self._control, start, end, text)
        return start, int(self._control.GetInsertionPoint())

    def text_between(self, start: int, end: int) -> str:
        return str(self._control.GetRange(max(0, start), end))

    def remove(self, start: int, end: int) -> None:
        self._control.Remove(start, end)
        self._control.SetInsertionPoint(start)

    def line_bounds(self) -> tuple[int, int]:
        text = self._control.GetValue()
        caret = int(self._control.GetInsertionPoint())
        start = text.rfind("\n", 0, caret) + 1
        newline = text.find("\n", caret)
        return start, len(text) if newline < 0 else newline

    def last_position(self) -> int:
        return int(self._control.GetLastPosition())

    def undo(self) -> bool:
        if not self._control.CanUndo():
            return False
        self._control.Undo()
        return True


class DictationReviewFrame(wx.Frame):
    """The review window: the words, what changed, the AI, and the six keys."""

    def __init__(
        self, parent: wx.Window | None, desk: ReviewDesk, *, context: bool, polish: bool = False
    ) -> None:
        super().__init__(parent, title=TITLE)
        self._desk = desk
        self.conversation: ReviewConversation | None = None
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        text_label = wx.StaticText(panel, label="Your &text, as it will be inserted:")
        self.text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2)
        set_accessible_name(self.text, "Your text, as it will be inserted")
        self.text.SetHelpText(
            "The words waiting to be inserted. Read them with the arrow keys, type "
            "to change them, or keep dictating: what you say is written here, not "
            "into the document. Nothing is inserted until you press Control Enter."
        )
        self.text.SetMinSize((-1, self.text.GetCharHeight() * 8))
        sizer.Add(text_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, _PAD)

        self.changes = _read_only(
            panel,
            sizer,
            "What c&hanged:",
            "",
            "What the last change did, worked out by comparing the words before and "
            "after it rather than taken from the AI. Control D says it again.",
            grow=False,
        )

        ask_label = wx.StaticText(panel, label="As&k the AI to change it, like make it shorter:")
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.instruction = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self.instruction, "Ask the AI to change it")
        self.instruction.SetHelpText(
            "Type what to change and press Enter: make it shorter, more formal, fix "
            "the grammar only. Only these words and your instruction are sent. Each "
            "one is one request."
        )
        self.send = wx.Button(panel, label="Se&nd to the AI")
        self.send.SetHelpText("Sends the instruction you typed, with the words above.")
        row.Add(self.instruction, 1, wx.EXPAND | wx.RIGHT, _PAD)
        row.Add(self.send, 0)
        sizer.Add(ask_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)

        self.talk = wx.CheckBox(panel, label="T&alk about it: everything I say is an instruction")
        self.talk.SetHelpText(
            "On: everything you say is an instruction for the AI, with no command "
            "word, and nothing you say is written into the text. Off: what you say "
            "is written into the text, and instructions start with the command word."
        )
        sizer.Add(self.talk, 0, wx.ALL, _PAD)

        self.context: wx.CheckBox | None = None
        if context:
            self.context = wx.CheckBox(
                panel, label="Include this document's dictation c&ontext with requests"
            )
            self.context.SetHelpText(
                "Sends the dictation context you chose for this document, such as a "
                "formal letter, with each request. Off by default: then only the "
                "words above and your instruction are sent."
            )
            sizer.Add(self.context, 0, wx.ALL, _PAD)

        self.status = _read_only(
            panel,
            sizer,
            "&Status:",
            "",
            "Where the words go, what each request costs, and whether one is on its way.",
            grow=False,
        )

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.insert = self._button(
            panel,
            buttons,
            "&Insert (Ctrl+Enter)",
            "Writes the text where it was "
            "going: the document, or the field in the other program. The only way "
            "anything is written.",
            lambda: self._run("insert"),
        )
        self.read = self._button(
            panel,
            buttons,
            "&Read It (Ctrl+R)",
            "Reads the whole text aloud.",
            lambda: self._run("read_it"),
        )
        self.what = self._button(
            panel,
            buttons,
            "&What Changed (Ctrl+D)",
            "Says again what the last change did.",
            lambda: self._run("what_changed"),
        )
        self.undo = self._button(
            panel,
            buttons,
            "&Undo Change (Ctrl+Z)",
            "Takes back the AI's last change. With none to take back, undoes your typing.",
            self._undo,
        )
        self.back = self._button(
            panel,
            buttons,
            "&Back to What I Said (Ctrl+Shift+Z)",
            "Puts back the words exactly as you said them.",
            lambda: self._run("restore"),
        )
        #: Polish (P3): only when the person allowed it; off by default.
        self.polish: wx.Button | None = None
        if polish:
            self.polish = self._button(
                panel,
                buttons,
                "&Polish (Ctrl+P)",
                "Asks the AI to fix punctuation, capital letters and small slips in "
                "the words, keeping your words and their order. One request; you hear "
                "what changed, and Undo Change takes it back.",
                lambda: self._run("polish"),
            )
        self.discard = self._button(
            panel,
            buttons,
            "&Discard (Escape)",
            "Throws the words away; nothing is written. Asks first if the AI has changed them.",
            self._escape,
        )
        close = wx.Button(panel, wx.ID_CLOSE, "Close")
        close.SetHelpText(
            "Closes the window without inserting. The words are kept, and Review "
            "Dictation brings them back."
        )
        buttons.Add(close, 0)
        bind_close_button(self, close, modeless=True)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)

        self.send.Bind(wx.EVT_BUTTON, lambda _e: self._send())
        self.instruction.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._send())
        self.text.Bind(wx.EVT_TEXT, self._on_text)
        if self.context is not None:
            self.context.Bind(wx.EVT_CHECKBOX, lambda _e: desk.set_context(self._context_on()))
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._keys()
        self.SetInitialSize(dip_size(self, 700, 560))
        self.Centre()
        focus_on(self, self.text)

    # -- building ----------------------------------------------------------- #

    def _button(
        self, panel: wx.Panel, row: wx.BoxSizer, label: str, help_text: str, run: Any
    ) -> wx.Button:
        button = wx.Button(panel, label=label)
        button.SetHelpText(help_text)
        button.Bind(wx.EVT_BUTTON, lambda _e: run())
        row.Add(button, 0, wx.RIGHT | wx.BOTTOM, _PAD)
        return button

    def _keys(self) -> None:
        table = [
            (wx.ACCEL_CTRL, wx.WXK_RETURN, lambda: self._run("insert")),
            (wx.ACCEL_CTRL, ord("R"), lambda: self._run("read_it")),
            (wx.ACCEL_CTRL, ord("D"), lambda: self._run("what_changed")),
            (wx.ACCEL_CTRL, ord("Z"), self._undo),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("Z"), lambda: self._run("restore")),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, self._escape),
        ]
        if self.polish is not None:
            table.append((wx.ACCEL_CTRL, ord("P"), lambda: self._run("polish")))
        entries = []
        for flags, key, run in table:
            ident = wx.NewIdRef()
            self.Bind(wx.EVT_MENU, lambda _e, run=run: run(), id=ident)
            entries.append(wx.AcceleratorEntry(flags, key, ident))
        # Kept where bind_field_dictation looks, so an editor's Ctrl+F11 joins them.
        self._quill_accelerators = entries
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def start(self, conversation: ReviewConversation) -> None:
        """Show *conversation*'s words, and say nothing: the reader reads them."""
        self.conversation = conversation
        self.text.ChangeValue(conversation.session.current)
        self.text.SetInsertionPointEnd()
        self.changes.ChangeValue(conversation.session.last_summary)
        self.status.ChangeValue(conversation.opening_status())
        if conversation.ai_reason():
            for control in (self.instruction, self.send, self.talk, self.context, self.polish):
                if control is not None:
                    control.Enable(False)

    # -- what the controls do ------------------------------------------------- #

    def talking(self) -> bool:
        return bool(self.talk.IsEnabled() and self.talk.GetValue())

    def _context_on(self) -> bool:
        return bool(self.context is not None and self.context.GetValue())

    def _run(self, name: str) -> None:
        if self.conversation is not None:
            getattr(self.conversation, name)()

    def _send(self) -> None:
        if self.conversation is None:
            return
        instruction = self.instruction.GetValue()
        self.conversation.instruct(instruction)
        if self.conversation.working:
            self.instruction.ChangeValue("")

    def _undo(self) -> None:
        """Ctrl+Z: the AI's last change; with none, the typing in the text."""
        conversation = self.conversation
        if conversation is None:
            return
        if conversation.session.changed or not self.text.CanUndo():
            conversation.undo_change()
            return
        self.text.Undo()

    def _escape(self) -> None:
        """Escape: stop a request on its way, else Discard."""
        if self.conversation is None:
            return
        if not self.conversation.cancel():
            self.conversation.discard()

    def _on_text(self, event: wx.CommandEvent) -> None:
        event.Skip()
        if self.conversation is not None:
            self.conversation.edited(self.text.GetValue())

    def _on_close(self, event: wx.CloseEvent) -> None:
        self._desk.closed(self)
        event.Skip()  # the frame is destroyed


class _FramePort:
    """:class:`~quill.core.windows_dictation.review_conversation.ReviewPort`
    for the window and its host."""

    def __init__(self, desk: ReviewDesk, frame: DictationReviewFrame) -> None:
        self._desk = desk
        self._frame = frame

    def say(self, text: str) -> None:
        self._desk.host._review_say(text)

    def status(self, text: str) -> None:
        if self._frame:
            self._frame.status.ChangeValue(text)

    def show_text(self, text: str) -> None:
        if self._frame:
            self._frame.text.ChangeValue(text)
            self._frame.text.SetInsertionPoint(0)

    def show_changes(self, text: str) -> None:
        if self._frame:
            self._frame.changes.ChangeValue(text)

    def mute(self, text: str) -> None:
        from quill.ui.windows_dictation_hold import reply_seconds

        self._desk.host._review_mute(reply_seconds(text))

    def ask_yes_no(self, question: str, title: str) -> bool:
        answer = show_message_box(
            question, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self._frame
        )
        return bool(answer == wx.YES)

    def insert(self, text: str, original: str) -> None:
        self._desk.finish(self._frame)
        self._desk.host._review_insert(text, original)

    def close(self) -> None:
        self._desk.finish(self._frame)


class ReviewDesk:
    """One app's review: at most one window, and the voice commands' way in.

    The host (an editor's dictation mixin, or QUILL Transcribe) answers:

    * ``_review_parent()`` -- the window the review is parented to;
    * ``_review_say(text)`` -- a sentence, through the screen reader;
    * ``_review_ai()`` -- the AI route
      (:class:`~quill.core.windows_dictation.review_conversation.ReviewAi`), or
      ``None`` when this app has none;
    * ``_review_rescue_path()`` -- where an open review is kept;
    * ``_review_my_instructions()`` and ``_review_context()`` -- what goes with
      a request (the context only when the person turned it on);
    * ``_review_context_offered()``, ``_review_set_context(on)`` and
      ``_review_context_setting()`` -- the context check box, editors only;
    * ``_review_retarget(document)`` -- point dictation at the review's text,
      and back (``None``) when it closes;
    * ``_review_insert(text, original)`` -- put the words where they were going;
    * ``_review_mute(seconds)`` -- the microphone ignores the reader meanwhile.
    """

    def __init__(self, host: Any) -> None:
        self.host = host
        self.frame: DictationReviewFrame | None = None

    # -- what the controller asks (review_mixin.py) ------------------------------ #

    def is_open(self) -> bool:
        return bool(self.frame)

    def talking(self) -> bool:
        return bool(self.frame) and self.frame is not None and self.frame.talking()

    def ai_reason(self) -> str:
        ai = self.host._review_ai()
        if ai is None:
            return "AI is off."
        return str(ai.reason())

    def focus(self) -> None:
        if self.frame:
            wx.CallAfter(take_focus, self.frame)

    def command(self, command: Command) -> None:
        names = {
            Command.REVIEW_READ: "read_it",
            Command.REVIEW_WHAT_CHANGED: "what_changed",
            Command.REVIEW_UNDO: "undo_change",
            Command.REVIEW_RESTORE: "restore",
            Command.REVIEW_INSERT: "insert",
            Command.REVIEW_DISCARD: "discard",
            Command.REVIEW_POLISH: "polish",
        }
        name = names.get(command)
        if name is not None:
            defer(self._conversation_call, name)

    def instruct(self, text: str) -> None:
        defer(self._conversation_call, "instruct", text)

    def _conversation_call(self, name: str, *args: Any) -> None:
        frame = self.frame
        if frame and frame.conversation is not None:
            getattr(frame.conversation, name)(*args)

    # -- opening and closing ------------------------------------------------------- #

    def open(self, text: str) -> None:
        """Open the review with *text*; with none, what was kept from last time."""
        if self.frame:
            self.focus()
            return
        rescue = self.host._review_rescue_path()
        session = load_rescue(rescue) if not text.strip() else None
        if session is None:
            session = ReviewSession(text)
        frame = DictationReviewFrame(
            self.host._review_parent(),
            self,
            context=bool(self.host._review_context_offered()),
            polish=self._polish_on(),
        )
        if frame.context is not None:
            frame.context.SetValue(bool(self.host._review_context_setting()))
        conversation = ReviewConversation(
            session,
            _FramePort(self, frame),
            ai=self.host._review_ai(),
            rescue=rescue,
            my_instructions=self.host._review_my_instructions,
            context=lambda: self.host._review_context() if frame._context_on() else "",
            polish_on=self._polish_on,
        )
        frame.start(conversation)
        self.frame = frame
        self.host._review_retarget(ReviewBoxDocument(frame.text))
        bind = getattr(self.host, "_review_bind_keys", None)
        if callable(bind):
            bind(frame)  # an editor's Ctrl+F11 dictates into the text
        frame.Show()
        shown = getattr(self.host, "_review_shown", None)
        if callable(shown):
            shown(frame)  # QUILL Transcribe, from the tray: brought to the front
        wx.CallAfter(take_focus, frame)

    def set_context(self, on: bool) -> None:
        self.host._review_set_context(on)

    def _polish_on(self) -> bool:
        """Allow polishing my dictation with AI (P3): the host's setting, off."""
        hook = getattr(self.host, "_review_polish_on", None)
        try:
            return bool(hook()) if callable(hook) else False
        except Exception:  # noqa: BLE001 - unknown is off
            return False

    def finish(self, frame: DictationReviewFrame) -> None:
        """Inserted or discarded: close quietly, dictation back where it was."""
        if self.frame is frame:
            self.frame = None
            self.host._review_retarget(None)
        if frame:
            frame.conversation = None
            frame.Destroy()

    def closed(self, frame: DictationReviewFrame) -> None:
        """Closed another way (Close, Alt+F4, the app ending): the words are kept."""
        said = frame.conversation.closing() if frame.conversation is not None else ""
        frame.conversation = None
        if self.frame is frame:
            self.frame = None
            self.host._review_retarget(None)
        if said:
            self.host._review_say(said)

    def shut_down(self) -> None:
        """The app is closing: keep the words, say nothing."""
        frame = self.frame
        if frame:
            if frame.conversation is not None:
                frame.conversation.closing()
                frame.conversation = None
            self.frame = None
            frame.Destroy()
