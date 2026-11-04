"""The Schedule Publish window (wordpress.md 5.8): a date, a time and a time zone.

Three ordinary fields and nothing that floats. The window only collects what
was typed; :func:`quill.core.wordpress.schedule.parse_schedule` reads it, and
when it cannot, the command shows this window again with the reason in a
read-only Problem field at the top, so the fix is the first thing met.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import wx

from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.wordpress_dialogs import ShowModal, _buttons, labelled_row

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


@dataclass(frozen=True)
class ScheduleAnswer:
    date_text: str
    time_text: str
    zone_index: int


class ScheduleDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        purpose: str,
        date_text: str,
        time_text: str,
        zones: Sequence[str],
        zone_index: int,
        error: str = "",
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(purpose)
        sizer = wx.BoxSizer(wx.VERTICAL)
        if error:
            self.error = wx.TextCtrl(
                self, value=error, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL
            )
            self.error.SetHelpText(
                "Why the last date and time could not be used, and what to type."
            )
            labelled_row(sizer, self, "&Problem:", self.error)
        self.date = wx.TextCtrl(self, value=date_text)
        self.date.SetHelpText(
            "The day to publish, as year, month and day with hyphens, for example 2026-11-20."
        )
        labelled_row(sizer, self, "&Date (year-month-day):", self.date)
        self.time = wx.TextCtrl(self, value=time_text)
        self.time.SetHelpText(
            "The time to publish, in 24-hour hours and minutes such as 16:15, or like 4:15 PM."
        )
        labelled_row(sizer, self, "&Time:", self.time)
        self.zone = wx.Choice(self, choices=list(zones))
        self.zone.SetHelpText(
            "The time zone the date and time are in. The site's own time zone is first when the "
            "site says what it is; type a letter to jump to a city."
        )
        if zones:
            self.zone.SetSelection(max(0, min(zone_index, len(zones) - 1)))
        labelled_row(sizer, self, "Time &zone:", self.zone)
        sizer.Add(_buttons(self, "Schedule"), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(dip_size(self, 420, -1))
        apply_modal_ids(self)


def ask_schedule(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    purpose: str,
    date_text: str,
    time_text: str,
    zones: Sequence[str],
    zone_index: int = 0,
    error: str = "",
) -> ScheduleAnswer | None:
    dialog = ScheduleDialog(
        parent,
        title=title,
        purpose=purpose,
        date_text=date_text,
        time_text=time_text,
        zones=zones,
        zone_index=zone_index,
        error=error,
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return ScheduleAnswer(
            dialog.date.GetValue().strip(),
            dialog.time.GetValue().strip(),
            dialog.zone.GetSelection(),
        )
    finally:
        dialog.Destroy()
