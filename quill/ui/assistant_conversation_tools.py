"""Ask Quill's half of reading back, listing and exporting a conversation.

The behaviour is the shared :mod:`quill.ui.ai_conversation_tools`, the same
the AI Conversation window uses; this mixin is only where Ask Quill wires it
in, kept out of ``assistant_panel.py`` because that module is over its size
budget's comfort (GATE-11: extract rather than grow).

* **Message List...** and **Export Conversation...** sit in the footer beside
  Copy Last Response.
* **Alt+1 .. Alt+0** read the ten newest messages aloud: from the page
  through :class:`quill.ui.accessible_webview.AccessibleWebView`'s bridge, and
  from every other control in the window through the dialog's key hook.
* **The fallback reader.** When the WebView cannot start, the conversation is
  a plain list, one row per message. Enter on a row opens that message with
  its headings and tables, and closing it returns to the same row. A new
  message no longer moves the list's selection while the list has focus,
  because the selection *is* the reader's place; it follows the newest
  message only when nobody is reading the list.
"""

from __future__ import annotations

from typing import Any

from quill.ui.ai_conversation_tools import (
    RecentMessageReader,
    export_conversation_to_file,
    recent_digit,
    show_message_list,
    view_message,
)

__all__ = ["AssistantConversationToolsMixin"]


class AssistantConversationToolsMixin:
    """Message List, Export Conversation and the recent-ten keys for Ask Quill."""

    _transcript: list[tuple[str, str]]
    _announce: Any
    dialog: Any
    messages: Any

    def _build_conversation_tools(self, footer: Any) -> None:
        """Add the two buttons to *footer* and start the recent-ten reader."""
        import wx

        self._recent = RecentMessageReader(lambda: self._transcript, self._announce)
        self._list_position: int | None = None
        listed = wx.Button(self.dialog, label="Message &List...")
        listed.SetHelpText(
            "Lists every message in this conversation. Enter opens one with its "
            "headings and tables; closing it comes back to the same row. Alt+1 reads "
            "the newest message aloud wherever you are in this window, Alt+2 the one "
            "before, up to Alt+0 for the tenth newest."
        )
        listed.Bind(wx.EVT_BUTTON, lambda _e: self._on_message_list())
        export = wx.Button(self.dialog, label="E&xport Conversation...")
        export.SetHelpText(
            "Saves the whole conversation, every message with who said it, to a Word "
            "or text file you choose. Your document is not changed."
        )
        export.Bind(wx.EVT_BUTTON, lambda _e: self._on_export_conversation())
        footer.Add(listed, 0, wx.RIGHT, 8)
        footer.Add(export, 0, wx.RIGHT, 8)

    def _read_recent(self, n: int) -> None:
        self._recent.read(n)

    def _recent_from_key(self, event: Any) -> bool:
        """For the dialog's key hook: True when *event* was Alt and a digit."""
        n = recent_digit(event)
        if n:
            self._read_recent(n)
        return bool(n)

    def _on_message_list(self) -> None:
        self._list_position = show_message_list(
            self.dialog, self._transcript, self._announce, start=self._list_position
        )

    def _on_export_conversation(self) -> None:
        export_conversation_to_file(self.dialog, self._transcript, self._announce)

    # -- the fallback list (no WebView) ---------------------------------------

    def _bind_fallback_list(self) -> None:
        from quill.ui.dialog_contract import apply_listbox_activation

        #: For each row of the list, the message it shows (None: the greeting).
        self._fallback_rows: list[int | None] = []
        self.messages.SetHelpText(
            "The conversation, one message a row, newest at the end. Press Enter "
            "on a row to read that message in full with its headings and tables."
        )
        apply_listbox_activation(self.messages, lambda _e: self._open_fallback_row())

    def _fallback_show(self, display: str, message_index: int | None) -> None:
        """Add a row; follow it only when nobody is reading the list."""
        import wx

        rows = getattr(self, "_fallback_rows", None)
        if rows is not None:
            rows.append(message_index)
        index = self.messages.GetCount()
        self.messages.Append(display)
        if wx.Window.FindFocus() is self.messages and self.messages.GetSelection() >= 0:
            return
        self.messages.SetSelection(index)
        if hasattr(self.messages, "EnsureVisible"):
            self.messages.EnsureVisible(index)

    def _open_fallback_row(self) -> None:
        from quill.core.ai.chat_navigation import number_messages

        row = self.messages.GetSelection()
        rows = getattr(self, "_fallback_rows", [])
        target = rows[row] if 0 <= row < len(rows) else None
        if target is None:
            return
        view_message(self.dialog, number_messages(self._transcript)[target])
        self.messages.SetSelection(row)
        self.messages.SetFocus()
