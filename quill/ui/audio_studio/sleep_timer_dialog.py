"""Audio Studio Sleep Timer dialog (Phase 2 port-in).

A small modal dialog that edits a :class:`SleepTimerSetting` (enable, delay in
minutes, end-of-chapter) and returns it via :meth:`value`. The host starts the
watcher with the returned setting. Mirrors the house dialog style
(``apply_modal_ids``, stable ``name``); the standalone shell opens it with
``ShowModal``, embedded QUILL via ``_show_modal_dialog``.
"""

from __future__ import annotations

import wx

from quill.core.audio_studio.sleep_timer import SleepTimerSetting
from quill.core.i18n import _
from quill.ui.dialog_contract import apply_modal_ids

_MIN_MINUTES = 1
_MAX_MINUTES = 480


class SleepTimerDialog(wx.Dialog):
    """Edit a sleep-timer setting; ``value()`` reads the controls back."""

    def __init__(self, parent: wx.Window, setting: SleepTimerSetting) -> None:
        super().__init__(
            parent,
            title=str(_("Sleep Timer")),
            style=wx.DEFAULT_DIALOG_STYLE,
            name="audio_studio.sleep_timer",
        )
        self._setting = setting

        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label=str(_("Stop playback after a delay.")))
        sizer.Add(label, 0, wx.ALL, 8)

        self._enabled = wx.CheckBox(self, label=str(_("Sleep &timer enabled")))
        self._enabled.SetValue(setting.enabled)
        sizer.Add(self._enabled, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        delay_row = wx.BoxSizer(wx.HORIZONTAL)
        delay_row.Add(
            wx.StaticText(self, label=str(_("Delay (&minutes):"))),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT,
            8,
        )
        self._minutes = wx.SpinCtrl(
            self,
            value=str(int(max(_MIN_MINUTES, round(setting.delay_minutes)))),
            min=_MIN_MINUTES,
            max=_MAX_MINUTES,
            name="Sleep timer delay in minutes",
        )
        delay_row.Add(self._minutes, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        sizer.Add(delay_row, 0, wx.EXPAND | wx.BOTTOM, 8)

        self._end_of_chapter = wx.CheckBox(
            self, label=str(_("Stop at end of &chapter instead"))
        )
        self._end_of_chapter.SetValue(setting.end_of_chapter)
        sizer.Add(self._end_of_chapter, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)

        self._enabled.Bind(wx.EVT_CHECKBOX, self._on_enabled_toggle)
        self._sync_control_state()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _on_enabled_toggle(self, event: wx.CommandEvent) -> None:
        self._sync_control_state()
        event.Skip()

    def _sync_control_state(self) -> None:
        on = self._enabled.GetValue()
        self._minutes.Enable(on)
        self._end_of_chapter.Enable(on)

    def value(self) -> SleepTimerSetting:
        """Read the controls into a fresh :class:`SleepTimerSetting`."""
        return SleepTimerSetting(
            enabled=self._enabled.GetValue(),
            delay_minutes=float(self._minutes.GetValue()),
            end_of_chapter=self._end_of_chapter.GetValue(),
            last_started_at=self._setting.last_started_at,
        )