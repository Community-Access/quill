"""Verbosity chord mini-editor (verbosity §16).

A focused editor for the per-chord template overrides: pick a chord-fired verb,
give it a template that applies only when that chord triggers the verb. Backed by
the engine's per-chord override map; validation reuses the core parser. A11Y-4
hardened.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.verbosity.parser import validate
from quill.core.verbosity.registry import VerbRegistry, default_registry
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["VerbosityChordEditorDialog"]


class VerbosityChordEditorDialog:
    """Edit per-chord announcement overrides."""

    def __init__(
        self,
        parent: object,
        chord_verbs: dict[str, str],
        *,
        overrides: dict[str, str] | None = None,
        registry: VerbRegistry | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        # chord_verbs maps a chord label -> the verb id it fires.
        self._chord_verbs = dict(chord_verbs)
        self._chords = sorted(self._chord_verbs)
        self._overrides = dict(overrides or {})
        self._registry = registry or default_registry()
        self._announce = announce_cb or (lambda _m: None)
        self._result: dict[str, str] | None = None

        self.dialog = wx.Dialog(
            parent, title="Chord overrides", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(480, 360))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Chord:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE, choices=self._chords)
        self._list.SetName("Chord-fired verbs")
        self._list.SetMinSize(wx.Size(-1, 150))
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        root.Add(
            wx.StaticText(self.dialog, label="&Template for this chord:"), 0, wx.LEFT | wx.TOP, 8
        )
        self._template = wx.TextCtrl(self.dialog)
        self._template.SetName("Per-chord template")
        root.Add(self._template, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Chord override status")
        root.Add(self._status, 0, wx.LEFT | wx.TOP, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._apply_btn = wx.Button(self.dialog, label="&Apply to chord")
        self._clear_btn = wx.Button(self.dialog, label="C&lear chord")
        save_btn = wx.Button(self.dialog, id=wx.ID_SAVE, label="Sa&ve")
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Cancel")
        btns.Add(self._apply_btn, 0, wx.RIGHT, 6)
        btns.Add(self._clear_btn, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(save_btn, 0, wx.RIGHT, 6)
        btns.Add(cancel_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(
            self.dialog, affirmative_id=wx.ID_SAVE, affirmative_label="Save", cancel_id=wx.ID_CANCEL
        )

        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_select())
        self._apply_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_apply())
        self._clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_clear())
        save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save())
        cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        if self._chords:
            self._list.SetSelection(0)
            self._on_select()

    def _current_chord(self) -> str | None:
        index = self._list.GetSelection()
        return self._chords[index] if index >= 0 else None

    def _on_select(self) -> None:
        chord = self._current_chord()
        if chord is None:
            return
        self._template.SetValue(self._overrides.get(chord, ""))
        verb_id = self._chord_verbs[chord]
        self._status.SetLabel(f"{chord} fires {verb_id}")

    def _on_apply(self) -> None:
        chord = self._current_chord()
        if chord is None:
            return
        template = self._template.GetValue().strip()
        verb = self._registry.get(self._chord_verbs[chord])
        if template and verb is not None:
            report = validate(template, verb)
            if not report.ok:
                self._status.SetLabel(report.spoken_summary)
                self._announce(f"Cannot apply. {report.spoken_summary}")
                return
        if template:
            self._overrides[chord] = template
        else:
            self._overrides.pop(chord, None)
        self._announce(f"Applied override to {chord}")
        self._status.SetLabel(f"Override set for {chord}")

    def _on_clear(self) -> None:
        chord = self._current_chord()
        if chord is None:
            return
        self._overrides.pop(chord, None)
        self._template.SetValue("")
        self._announce(f"Cleared override for {chord}")

    def _on_save(self) -> None:
        self._result = dict(self._overrides)
        self.dialog.EndModal(wx.ID_SAVE)

    @property
    def overrides(self) -> dict[str, str] | None:
        return self._result

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CANCEL)
