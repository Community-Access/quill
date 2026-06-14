"""Dialog for enabling and disabling individual sound events.

Reads and writes ``settings.sound_events_disabled`` (comma-separated event IDs).

**Partial pack support**: only events actually present in the loaded pack(s)
are listed. If the active pack has no indent-level sounds (because no indent
tone pack is loaded), those checkboxes are absent. This keeps the dialog
focused: users only see toggles for sounds that will actually fire.

Pass ``loaded_events`` (a frozenset of event IDs from the active pack) to
``SoundEventsDialog.__init__`` so the dialog can filter accordingly.
"""

from __future__ import annotations

import wx

# Canonical display order, grouped by category.
# Events absent from the loaded pack are silently filtered out.
_EARCON_ORDER: list[str] = [
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

# Compare-mode events (issue #186) — shown only when the loaded pack maps them.
_COMPARE_ORDER: list[str] = [
    "compare_enter_mode",
    "compare_exit_mode",
    "compare_next_difference",
    "compare_previous_difference",
    "compare_no_more_differences",
]

# Indent level events — shown only when an indent tone pack is loaded.
# Listed in ascending level order; each level has _up and _down variants.
_INDENT_ORDER: list[str] = [
    event
    for level in range(8)
    for event in (f"indent_level_{level}_up", f"indent_level_{level}_down")
]

_EARCON_LABELS: dict[str, str] = {
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
    "compare_enter_mode": "Compare opened",
    "compare_exit_mode": "Compare closed",
    "compare_next_difference": "Compare: next difference",
    "compare_previous_difference": "Compare: previous difference",
    "compare_no_more_differences": "Compare: no more differences",
}

# Auto-generate labels for all 16 indent events.
_INDENT_LABELS: dict[str, str] = {
    f"indent_level_{level}_up": f"Indentation level {level} — going deeper" for level in range(8)
} | {f"indent_level_{level}_down": f"Indentation level {level} — dedenting" for level in range(8)}

_ALL_LABELS: dict[str, str] = {**_EARCON_LABELS, **_INDENT_LABELS}


class SoundEventsDialog(wx.Dialog):
    """Toggle individual sound events on or off.

    Parameters
    ----------
    parent:
        Parent window.
    disabled:
        Set of event IDs currently silenced (from ``settings.sound_events_disabled``).
    loaded_events:
        Event IDs present in the active pack(s).  Only events in this set are
        shown.  Pass ``None`` to show all known events (legacy / no-pack mode).
    """

    def __init__(
        self,
        parent: wx.Window,
        disabled: frozenset[str],
        loaded_events: frozenset[str] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title="Sound Events",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.SetName("Sound Events")

        # Filter earcon events to those present in the loaded pack.
        earcon_events = [
            eid for eid in _EARCON_ORDER if loaded_events is None or eid in loaded_events
        ]
        compare_events = [
            eid for eid in _COMPARE_ORDER if loaded_events is None or eid in loaded_events
        ]
        indent_events = [
            eid for eid in _INDENT_ORDER if loaded_events is None or eid in loaded_events
        ]
        has_indent = bool(indent_events)

        note = "Check events to enable their sound. Uncheck to silence individual events."
        if loaded_events is not None:
            shown = len(earcon_events) + len(compare_events) + len(indent_events)
            total = len(loaded_events)
            if shown < total:
                note += f" Showing {shown} of {total} events from the loaded pack."

        instruction = wx.StaticText(self, label=note)

        scroll = wx.ScrolledWindow(self, style=wx.VSCROLL | wx.BORDER_SIMPLE)
        scroll.SetScrollRate(0, 20)
        scroll.SetMinSize(wx.Size(460, 360))

        inner = wx.BoxSizer(wx.VERTICAL)
        self._checkboxes: list[tuple[str, wx.CheckBox]] = []

        if earcon_events:
            self._add_section(scroll, inner, "Earcons", earcon_events, disabled)

        if compare_events:
            inner.AddSpacer(10)
            self._add_section(scroll, inner, "Compare", compare_events, disabled)

        if has_indent:
            inner.AddSpacer(10)
            self._add_section(scroll, inner, "Indentation tones", indent_events, disabled)

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

    def _add_section(
        self,
        parent: wx.ScrolledWindow,
        sizer: wx.BoxSizer,
        heading: str,
        event_ids: list[str],
        disabled: frozenset[str],
    ) -> None:
        lbl = wx.StaticText(parent, label=heading)
        font = lbl.GetFont()
        font.MakeBold()
        lbl.SetFont(font)
        sizer.Add(lbl, 0, wx.LEFT | wx.TOP, 8)

        for eid in event_ids:
            label = _ALL_LABELS.get(eid, eid)
            cb = wx.CheckBox(parent, label=label)
            cb.SetValue(eid not in disabled)
            sizer.Add(cb, 0, wx.LEFT | wx.TOP | wx.RIGHT, 6)
            self._checkboxes.append((eid, cb))

    def _on_enable_all(self, _event: wx.CommandEvent) -> None:
        for _eid, cb in self._checkboxes:
            cb.SetValue(True)

    def _on_disable_all(self, _event: wx.CommandEvent) -> None:
        for _eid, cb in self._checkboxes:
            cb.SetValue(False)

    def get_disabled(self) -> str:
        """Return comma-separated event IDs that are unchecked (silenced)."""
        return ",".join(eid for eid, cb in self._checkboxes if not cb.GetValue())
