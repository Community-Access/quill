"""The Quiet Hours window: when the apps stop speaking on their own (11.9).

One shared surface, because the window is shared: a quiet hour is a fact
about the listener, not about which app happens to be open. The house dialog
pattern -- labelled controls, a readout that says what the setting does *and*
what it does not do, OK/Cancel through the dialog contract.

The readout is the load-bearing part. "Quiet hours" is a name people will
read as "the app goes deaf" or "feeds stop being checked", and neither is
true: everything still happens, and everything you press a key for still
answers. Saying that where the switch is is cheaper than saying it in a
support email.
"""

from __future__ import annotations

from typing import Any

from quill.core import quiet_hours
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Quiet Hours"

#: The choices, on the half hour. A spin control over 1,440 minutes is a
#: worse answer than a list somebody can arrow through in a few presses.
_CLOCK_CHOICES: tuple[str, ...] = tuple(
    f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)
)


def _index_of(value: str, fallback: str) -> int:
    for index, candidate in enumerate(_CLOCK_CHOICES):
        if candidate == value:
            return index
    return _CLOCK_CHOICES.index(fallback)


def show_quiet_hours(host: Any) -> None:
    """Open Quiet Hours. Modal, house pattern; saves on OK."""
    import wx

    from quill.core.paths import app_data_dir
    from quill.ui import quiet_hours_ui

    data_dir = app_data_dir()
    hours = quiet_hours.load_quiet_hours(data_dir)

    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)

    enable = wx.CheckBox(dialog, label="&Quiet hours on")
    enable.SetValue(hours.enabled)
    enable.SetHelpText(
        "Holds back the announcements the apps make on their own -- check "
        "ticks, new-episode notices, download notices. It does not stop feeds "
        "being checked or downloads running, and anything you press a key for "
        "still answers."
    )
    root.Add(enable, 0, wx.ALL, 10)

    grid = wx.FlexGridSizer(rows=2, cols=2, vgap=6, hgap=8)
    grid.Add(wx.StaticText(dialog, label="&From:"), 0, wx.ALIGN_CENTER_VERTICAL)
    start = wx.Choice(dialog, choices=list(_CLOCK_CHOICES))
    start.SetName("Quiet hours start time")
    start.SetSelection(_index_of(hours.start, quiet_hours.DEFAULT_START))
    start.SetHelpText("When the quiet window begins. A window may cross midnight.")
    grid.Add(start, 0)
    grid.Add(wx.StaticText(dialog, label="&To:"), 0, wx.ALIGN_CENTER_VERTICAL)
    end = wx.Choice(dialog, choices=list(_CLOCK_CHOICES))
    end.SetName("Quiet hours end time")
    end.SetSelection(_index_of(hours.end, quiet_hours.DEFAULT_END))
    end.SetHelpText("When it ends. Set both the same to mean no window at all.")
    grid.Add(end, 0)
    root.Add(grid, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    reminders = wx.CheckBox(dialog, label="Let &reminders through anyway")
    reminders.SetValue(hours.allow_reminders)
    reminders.SetHelpText(
        "Reminders are the one thing somebody may want *during* the quiet "
        "window -- an alarm clock is the reason to set one. Off means quiet "
        "means quiet. Failures always speak, whatever this says."
    )
    root.Add(reminders, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    readout = wx.StaticText(dialog, label=quiet_hours.describe(hours))
    readout.SetName("What quiet hours will do")
    root.Add(readout, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    ok_btn = wx.Button(dialog, wx.ID_OK, "&OK")
    ok_btn.SetHelpText("Saves the window. It applies to both Quill Radio and QUILL Cast.")
    cancel_btn = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
    cancel_btn.SetHelpText("Closes without changing anything.")
    buttons.Add(ok_btn, 0, wx.RIGHT, 6)
    buttons.Add(cancel_btn, 0)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    apply_modal_ids(dialog, affirmative_id=ok_btn.GetId(), escape_id=cancel_btn.GetId())
    dialog.SetSizerAndFit(root)

    def _preview(_event: Any) -> None:
        readout.SetLabel(quiet_hours.describe(_gathered()))

    def _gathered() -> quiet_hours.QuietHours:
        return quiet_hours.QuietHours(
            enabled=bool(enable.GetValue()),
            start=_CLOCK_CHOICES[max(0, start.GetSelection())],
            end=_CLOCK_CHOICES[max(0, end.GetSelection())],
            allow_reminders=bool(reminders.GetValue()),
        )

    enable.Bind(wx.EVT_CHECKBOX, _preview)
    reminders.Bind(wx.EVT_CHECKBOX, _preview)
    start.Bind(wx.EVT_CHOICE, _preview)
    end.Bind(wx.EVT_CHOICE, _preview)

    try:
        if host._show_modal_dialog(dialog, TITLE) != wx.ID_OK:
            return
        chosen = _gathered()
    finally:
        dialog.Destroy()
    quiet_hours.save_quiet_hours(data_dir, chosen)
    quiet_hours_ui.invalidate()
    host._announce(quiet_hours.describe(chosen))
