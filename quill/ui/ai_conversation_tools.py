"""Reading back, listing and exporting an AI conversation.

Shared by both conversation windows -- Ask Quill in QUILL
(:mod:`quill.ui.assistant_conversation_tools`) and the AI Conversation window
both editors open (:mod:`quill.ui.hosted_ai_chat`) -- so the two behave alike
and QUILL Lite gets everything the AI Conversation window gets (CLAUDE.md:
Lite may never be ahead of QUILL, and neither may QUILL be ahead where both
have the window). The counting and wording live in the wx-free
:mod:`quill.core.ai.chat_navigation`; the files are written by
:func:`quill.core.ai.chat_export.export_conversation`.

Three things, all reached from buttons in each window and from keys:

* **The recent ten** -- Alt+1 reads the newest message, Alt+2 the one before,
  to Alt+0 for the tenth newest. Read aloud only: focus stays in the message
  box, and a reply arriving while one is being read changes nothing about
  where anybody is.
* **Messages...** -- every message in a list, "Message 3 of 12, AI" and its
  opening words. Enter opens one in a reading window where its headings and
  tables are real ones (browse mode: H for headings, T for tables, Ctrl+Alt
  and the arrows inside a table); **Read as Text** shows the same message as
  plain text in an edit field instead, for a reader or a moment when browse
  mode is not wanted. Closing either lands back on the same row, and the list
  opens on that row next time too.
* **Export Conversation...** -- the whole conversation, every message with
  its speaker and in order, to a Word or text file chosen in the ordinary
  Save As window, which asks before replacing a file. The document being
  written in the editor is never touched.

Every control has its F1 sentence at construction; OK, Cancel and Close carry
no access key (GATE-14).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import wx

from quill.core.ai.chat_navigation import (
    RECENT_COUNT,
    ChatMessage,
    message_view_html,
    number_messages,
    recent_message_sentence,
    row_label,
)
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)

__all__ = [
    "LIST_TITLE",
    "TEXT_TITLE",
    "MessageListDialog",
    "RecentMessageReader",
    "bind_recent_message_keys",
    "export_conversation_to_file",
    "read_message_as_text",
    "show_message_list",
    "view_message",
]

LIST_TITLE = "Conversation Messages"
TEXT_TITLE = "Message Text"

#: The Save As window's choices, in order; the first is the default.
_EXPORT_CHOICES: tuple[tuple[str, str], ...] = (
    ("Word document (*.docx)|*.docx", ".docx"),
    ("Text file (*.txt)|*.txt", ".txt"),
)

Pairs = Sequence[tuple[str, str]]


# --------------------------------------------------------------------------- #
# The recent ten
# --------------------------------------------------------------------------- #


class RecentMessageReader:
    """Alt+1 .. Alt+0: read one of the newest ten messages aloud.

    One reader per window. *get_pairs* returns the conversation as it stands
    when the key is pressed, so a reply that arrived a moment ago is already
    the newest. The same key arriving twice within a fraction of a second is
    said once: in Ask Quill the page and the window can both see one press.
    """

    def __init__(self, get_pairs: Callable[[], Pairs], announce: Callable[[str], None]) -> None:
        self._get_pairs = get_pairs
        self._announce = announce
        self._last: tuple[int, float] = (0, 0.0)

    def read(self, n: int) -> str:
        """Say the *n*-th newest message; return what was said."""
        now = time.monotonic()
        if self._last[0] == n and now - self._last[1] < 0.3:
            return ""
        self._last = (n, now)
        sentence = recent_message_sentence(number_messages(self._get_pairs()), n)
        self._announce(sentence)
        return sentence


def bind_recent_message_keys(window: wx.Window, reader: RecentMessageReader) -> list[int]:
    """Give *window* Alt+1 .. Alt+0 through an accelerator table.

    Returns the command ids, oldest-key first, so a test can fire one. The
    table is the window's only one: neither conversation window had one.
    """
    entries: list[wx.AcceleratorEntry] = []
    ids: list[int] = []
    for n in range(1, RECENT_COUNT + 1):
        command = wx.NewIdRef()
        ids.append(int(command))
        digit = ord(str(n % 10))
        entries.append(wx.AcceleratorEntry(wx.ACCEL_ALT, digit, int(command)))
        window.Bind(wx.EVT_MENU, lambda _e, k=n: reader.read(k), id=int(command))
    window.SetAcceleratorTable(wx.AcceleratorTable(entries))
    return ids


def recent_digit(event: Any) -> int:
    """For a char hook: 1..10 when *event* is Alt plus a digit, else 0."""
    if not event.AltDown() or event.ControlDown() or event.ShiftDown():
        return 0
    key = event.GetKeyCode()
    for base in (ord("0"), wx.WXK_NUMPAD0):
        if base <= key <= base + 9:
            return (key - base) or 10
    return 0


# --------------------------------------------------------------------------- #
# Messages...
# --------------------------------------------------------------------------- #


class MessageListDialog(wx.Dialog):
    """Every message in one list; Enter reads one, and comes back to the row."""

    def __init__(
        self,
        parent: wx.Window | None,
        messages: list[ChatMessage],
        *,
        start: int | None = None,
        view: Callable[[wx.Window, ChatMessage], None] | None = None,
        read: Callable[[wx.Window, ChatMessage], None] | None = None,
    ) -> None:
        super().__init__(parent, title=LIST_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._messages = messages
        self._view = view or view_message
        self._read = read or read_message_as_text

        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Messages")
        self.list = wx.ListBox(self, style=wx.LB_SINGLE)
        set_accessible_name(self.list, "Messages")
        self.list.SetHelpText(
            "Every message in this conversation, oldest first: its number, who said "
            "it and its opening words. Press Enter to read one in full; closing it "
            "brings you back to this row."
        )
        self.list.Set([row_label(message) for message in messages])
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._open = wx.Button(self, label="&Open")
        self._open.SetHelpText(
            "Opens the chosen message in a reading window where its headings and "
            "tables are real ones: H moves by heading and T by table in browse mode."
        )
        self._text = wx.Button(self, label="Read as &Text")
        self._text.SetHelpText(
            "Shows the chosen message exactly as it arrived, in a plain text field "
            "you can arrow through, select and copy."
        )
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes the list and goes back to the conversation.")
        buttons.Add(self._open, 0, wx.RIGHT, 8)
        buttons.Add(self._text, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(close, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(sizer)

        self._open.Bind(wx.EVT_BUTTON, lambda _e: self.open_current())
        self._text.Bind(wx.EVT_BUTTON, lambda _e: self.read_current())
        apply_listbox_activation(self.list, lambda _e: self.open_current())
        bind_close_button(self, close, modeless=False)
        apply_modal_ids(self, escape_id=wx.ID_CANCEL)

        if messages:
            last = len(messages) - 1
            chosen = last if start is None else max(0, min(start, last))
            self.list.SetSelection(chosen)
        self.SetInitialSize((620, 440))
        self.list.SetFocus()

    @property
    def position(self) -> int:
        """The row the list is on, or -1."""
        return int(self.list.GetSelection())

    def _current(self) -> ChatMessage | None:
        index = self.position
        return self._messages[index] if 0 <= index < len(self._messages) else None

    def open_current(self) -> None:
        self._show(self._view)

    def read_current(self) -> None:
        self._show(self._read)

    def _show(self, how: Callable[[wx.Window, ChatMessage], None]) -> None:
        message = self._current()
        if message is None:
            return
        index = self.position
        how(self, message)
        # Back where the reader left: the same row, with focus on the list.
        if self:
            self.list.SetSelection(index)
            self.list.SetFocus()


def show_message_list(
    parent: wx.Window | None,
    pairs: Pairs,
    announce: Callable[[str], None],
    *,
    start: int | None = None,
) -> int | None:
    """Show the list; return the row it was left on, to start there next time."""
    messages = number_messages(pairs)
    if not messages:
        announce("No messages yet.")
        return start
    dialog = MessageListDialog(parent, messages, start=start)
    try:
        show_modal_dialog(dialog, LIST_TITLE)
        return dialog.position
    finally:
        dialog.Destroy()


def view_message(parent: wx.Window, message: ChatMessage) -> None:
    """One message, rendered: real headings and tables for browse mode."""
    from quill.ui.preview_dialog import MarkdownPreviewDialog

    MarkdownPreviewDialog(parent, message.position, message_view_html(message)).show()


class _MessageTextDialog(wx.Dialog):
    """One message as plain text, exactly as it arrived."""

    def __init__(self, parent: wx.Window | None, message: ChatMessage) -> None:
        super().__init__(parent, title=TEXT_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=f"&{message.position}"), 0, wx.ALL, 8)
        self.text = wx.TextCtrl(
            self, value=message.text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        set_accessible_name(self.text, message.position)
        self.text.SetHelpText(
            "The message exactly as it arrived, Markdown and all. Arrow through it, "
            "or select and copy any of it."
        )
        self.text.SetMinSize((560, 300))
        sizer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes this and goes back to the list of messages.")
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        row.Add(close, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        bind_close_button(self, close, modeless=False)
        apply_modal_ids(self, escape_id=wx.ID_CANCEL)
        self.text.SetInsertionPoint(0)
        self.text.SetFocus()


def read_message_as_text(parent: wx.Window, message: ChatMessage) -> None:
    """Read as Text: the message in a read-only edit field."""
    dialog = _MessageTextDialog(parent, message)
    try:
        show_modal_dialog(dialog, TEXT_TITLE)
    finally:
        dialog.Destroy()


# --------------------------------------------------------------------------- #
# Export Conversation...
# --------------------------------------------------------------------------- #


def _choose_export_path(parent: wx.Window | None, default_name: str) -> Path | None:
    """The ordinary Save As window; it asks before replacing a file."""
    wildcard = "|".join(choice for choice, _suffix in _EXPORT_CHOICES)
    with wx.FileDialog(  # dialog_button_contract: exempt
        parent,
        "Export Conversation",
        defaultFile=f"{default_name}{_EXPORT_CHOICES[0][1]}",
        wildcard=wildcard,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        path = Path(dialog.GetPath())
        index = dialog.GetFilterIndex()
    if path.suffix.lower() not in {suffix for _choice, suffix in _EXPORT_CHOICES}:
        path = path.with_name(path.name + _EXPORT_CHOICES[max(0, index)][1])
    return path


def export_conversation_to_file(
    parent: wx.Window | None,
    pairs: Pairs,
    announce: Callable[[str], None],
    *,
    default_name: str = "AI conversation",
    choose: Callable[[wx.Window | None, str], Path | None] | None = None,
) -> Path | None:
    """Export Conversation: choose a file, write it, say what happened.

    Cancelling says nothing (the reader already says focus came back). A
    file that will not write is said in words and leaves any earlier file at
    that name as it was, because the writers are atomic.
    """
    from quill.core.ai.chat_export import export_conversation

    if not pairs:
        announce("There is nothing in this conversation to export yet.")
        return None
    target = (choose or _choose_export_path)(parent, default_name)
    if target is None:
        return None
    try:
        written = export_conversation(list(pairs), target, title=default_name)
    except Exception as error:  # noqa: BLE001 - every failure is said, none crashes the window
        from quill.core.error_codes import user_facing_message

        announce(f"Could not export the conversation. {user_facing_message(error)}")
        return None
    count = len(pairs)
    noun = "message" if count == 1 else "messages"
    announce(f"Exported {count} {noun} to {written.name}.")
    return written
