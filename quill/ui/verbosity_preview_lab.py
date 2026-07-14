"""Preview Lab dialog (verbosity §23).

Test the current profile / templates / channel mix against the fourteen canned
scenarios and read each scenario's per-channel output side by side. Backed by the
pure :mod:`quill.core.verbosity.preview` renderer driven by a
:class:`~quill.core.verbosity.engine.VerbosityEngine`. A11Y-4 hardened.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.verbosity.engine import VerbosityEngine
from quill.core.verbosity.preview import BUILTIN_SCENARIOS, preview_scenario
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["VerbosityPreviewLabDialog"]


class VerbosityPreviewLabDialog:
    """Preview built-in scenarios under a chosen engine configuration."""

    def __init__(
        self,
        parent: object,
        engine: VerbosityEngine | None = None,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._engine = engine or VerbosityEngine()
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent, title="Verbosity preview lab", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(600, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Scenario:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(
            self.dialog, style=wx.LB_SINGLE, choices=[s.name for s in BUILTIN_SCENARIOS]
        )
        self._list.SetName("Preview scenarios")
        self._list.SetMinSize(wx.Size(-1, 170))
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        root.Add(wx.StaticText(self.dialog, label="&Output:"), 0, wx.LEFT | wx.TOP, 8)
        self._output = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._output.SetName("Scenario output")
        self._output.SetMinSize(wx.Size(-1, 150))
        root.Add(self._output, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._speak_btn = wx.Button(self.dialog, label="&Speak this scenario")
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="C&lose")
        btns.Add(self._speak_btn, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_select())
        self._speak_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_speak())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        if BUILTIN_SCENARIOS:
            self._list.SetSelection(0)
            self._on_select()

    def _current_output(self):
        index = self._list.GetSelection()
        if index < 0:
            return None
        return preview_scenario(BUILTIN_SCENARIOS[index], self._engine)

    def _on_select(self) -> None:
        out = self._current_output()
        if out is None:
            return
        lines = [
            f"Scenario: {out.scenario_name}",
            f"Profile: {out.profile}",
            f"Channels: {out.channels}",
            f"Template source: {out.template_source}",
            f"Speech: {out.speech or '(silent)'}",
            f"Braille: {out.braille or '(none)'}",
            f"Visual: {out.visual}",
            f"Sound: {out.sound_event or '(none)'}",
        ]
        if out.suppressed:
            lines.append(f"Suppressed: {out.suppressed}")
        self._output.SetValue("\n".join(lines))

    def _on_speak(self) -> None:
        out = self._current_output()
        if out is not None:
            self._announce(out.speech or out.visual)

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CLOSE)
