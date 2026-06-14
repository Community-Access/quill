"""Dialog for enabling and disabling individual sound events.

Reads and writes ``settings.sound_events_disabled`` (comma-separated event IDs).
All events from :class:`~quill.core.sound_events.SoundEvent` are listed as
individual checkboxes inside a scrollable panel. Checked = sound plays;
unchecked = silenced.
"""

from __future__ import annotations

import wx

_EVENT_ORDER = [
    # Editing
    "abbreviation_expanded",
    "abbreviation_deleted",
    "snippet_inserted",
    "autocomplete_accepted",
    "word_corrected",
    # Document lifecycle
    "document_created",
    "document_saved",
    "document_closed",
    # Navigation
    "browse_mode_on",
    "browse_mode_off",
    "heading_jumped",
    "table_entered",
    "list_entered",
    # Search
    "search_found",
    "search_not_found",
    "search_wrapped",
    # AI and transcription
    "ai_thinking_started",
    "ai_response_received",
    "ai_error",
    "transcription_started",
    "transcription_stopped",
    "transcription_word_inserted",
    # Connectivity
    "ssh_connected",
    "ssh_disconnected",
    # System
    "error",
    "warning",
    "sound_on",
    "sound_off",
]

_EVENT_LABELS: dict[str, str] = {
    "abbreviation_expanded": "Abbreviation expanded",
    "abbreviation_deleted": "Abbreviation deleted (backspace after expansion)",
    "snippet_inserted": "Snippet inserted",
    "autocomplete_accepted": "Autocomplete accepted",
    "word_corrected": "Word auto-corrected",
    "document_created": "Document created",
    "document_saved": "Document saved",
    "document_closed": "Document closed",
    "browse_mode_on": "Browse mode on",
    "browse_mode_off": "Browse mode off",
    "heading_jumped": "Heading jumped",
    "table_entered": "Table entered",
    "list_entered": "List entered",
    "search_found": "Search found",
    "search_not_found": "Search not found",
    "search_wrapped": "Search wrapped (back to top)",
    "ai_thinking_started": "AI thinking started",
    "ai_response_received": "AI response received",
    "ai_error": "AI error",
    "transcription_started": "Transcription started",
    "transcription_stopped": "Transcription stopped",
    "transcription_word_inserted": "Transcription word inserted",
    "ssh_connected": "SSH connected",
    "ssh_disconnected": "SSH disconnected",
    "error": "Error",
    "warning": "Warning",
    "sound_on": "Sound notifications turned on",
    "sound_off": "Sound notifications turned off",
}


class SoundEventsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, disabled: frozenset[str]) -> None:
        super().__init__(
            parent,
            title="Sound Events",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        instruction = wx.StaticText(
            self,
            label="Check events to enable their sound. Uncheck to silence individual events.",
        )

        # Scrollable panel of individual CheckBox controls (A11Y-SR-1: screen
        # readers announce checked state correctly for wx.CheckBox).
        scroll = wx.ScrolledWindow(self, style=wx.VSCROLL | wx.BORDER_SIMPLE)
        scroll.SetScrollRate(0, 20)
        scroll.SetMinSize(wx.Size(440, 320))

        inner = wx.BoxSizer(wx.VERTICAL)
        self._checkboxes: list[tuple[str, wx.CheckBox]] = []
        for eid in _EVENT_ORDER:
            label = _EVENT_LABELS.get(eid, eid)
            cb = wx.CheckBox(scroll, label=label)
            cb.SetValue(eid not in disabled)
            inner.Add(cb, 0, wx.LEFT | wx.TOP | wx.RIGHT, 6)
            self._checkboxes.append((eid, cb))
        inner.AddSpacer(6)
        scroll.SetSizer(inner)

        btn_enable = wx.Button(self, label="Enable &All")
        btn_disable = wx.Button(self, label="&Disable All")
        btn_ok = wx.Button(self, wx.ID_OK, label="OK")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()

        top = wx.BoxSizer(wx.VERTICAL)
        top.Add(instruction, 0, wx.ALL, 8)
        top.Add(scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        bulk_row = wx.BoxSizer(wx.HORIZONTAL)
        bulk_row.Add(btn_enable, 0, wx.RIGHT, 6)
        bulk_row.Add(btn_disable)
        top.Add(bulk_row, 0, wx.LEFT | wx.BOTTOM, 8)

        btn_row = wx.StdDialogButtonSizer()
        btn_row.AddButton(btn_ok)
        btn_row.AddButton(btn_cancel)
        btn_row.Realize()
        top.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizerAndFit(top)

        btn_enable.Bind(wx.EVT_BUTTON, self._on_enable_all)
        btn_disable.Bind(wx.EVT_BUTTON, self._on_disable_all)

    def _on_enable_all(self, _event: wx.CommandEvent) -> None:
        for _eid, cb in self._checkboxes:
            cb.SetValue(True)

    def _on_disable_all(self, _event: wx.CommandEvent) -> None:
        for _eid, cb in self._checkboxes:
            cb.SetValue(False)

    def get_disabled(self) -> str:
        """Return comma-separated event IDs that are unchecked (silenced)."""
        return ",".join(eid for eid, cb in self._checkboxes if not cb.GetValue())
