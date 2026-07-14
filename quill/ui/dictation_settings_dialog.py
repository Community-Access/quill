"""Dictation Settings dialog (§1.2 dictation follow-ups).

An accessible, keyboard-operable panel over the dictation knobs already stored in
``settings`` (the ``DictationConfig`` the controller reads): the Locked-Dictation
time cap, stop-on-focus-loss, intelligent insertion spacing, and a reset for the
one-time first-use hint. (The "minimum hold" knob was removed along with
Hold-to-Dictate; the core config field remains at its 0.0 default.) The caller
owns the ``wx.Dialog`` so the hardened modal path and ``apply_modal_ids``
live in one place; on OK the chosen values are exposed as ``result``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DictationSettingsResult:
    """The values chosen in the dialog (applied to ``settings`` by the caller)."""

    max_locked_seconds: float
    stop_on_focus_loss: bool
    intelligent_spacing: bool
    reset_onboarding: bool


class DictationSettingsDialog:
    """Builds the dictation-settings controls and exposes the choice after OK."""

    def __init__(self, wx: Any, *, settings: Any) -> None:
        self._wx = wx
        self._settings = settings
        self.result: DictationSettingsResult | None = None
        self.dialog: Any = None
        self._outer_sizer: Any = None

    def populate(self, dlg: Any) -> Any:
        wx = self._wx
        self.dialog = dlg
        outer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(0, 2, 8, 10)
        grid.AddGrowableCol(1, 1)

        def _add(label_text: str, factory: Any) -> Any:
            # Create the label BEFORE the control (via a factory) so it precedes its
            # field in tab order — the A11Y z-order contract (dialog z-order gate).
            grid.Add(wx.StaticText(dlg, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)
            control = factory()
            grid.Add(control, 0, wx.EXPAND)
            return control

        self._max_locked = _add(
            "&Locked Dictation time limit (seconds):",
            lambda: wx.SpinCtrl(dlg, min=30, max=3600),
        )
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

        self._focus_loss = wx.CheckBox(dlg, label="Stop and &keep speech when QUILL loses focus")
        outer.Add(self._focus_loss, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self._spacing = wx.CheckBox(dlg, label="&Intelligent insertion spacing")
        outer.Add(self._spacing, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self._reset_hint = wx.CheckBox(dlg, label="Show the first-use &hint again next time")
        outer.Add(self._reset_hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        dlg.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._outer_sizer = outer
        return outer

    def finalize(self) -> None:
        s = self._settings
        self.dialog.SetSizerAndFit(self._outer_sizer)
        max_locked = float(getattr(s, "dictation_max_locked_seconds", 300.0))
        self._max_locked.SetValue(int(round(max_locked)))
        self._focus_loss.SetValue(bool(getattr(s, "dictation_stop_on_focus_loss", True)))
        self._spacing.SetValue(bool(getattr(s, "dictation_intelligent_spacing", True)))
        self._reset_hint.SetValue(False)

    def _on_ok(self, event: Any) -> None:
        self.result = DictationSettingsResult(
            max_locked_seconds=float(self._max_locked.GetValue()),
            stop_on_focus_loss=self._focus_loss.GetValue(),
            intelligent_spacing=self._spacing.GetValue(),
            reset_onboarding=self._reset_hint.GetValue(),
        )
        event.Skip()  # let the dialog close with ID_OK
