"""Setting a reminder, on anything (list.md 7.1, 7.2, 7.3, 7.8).

The calendar shipped with a one-question version of this -- a list of lead
times -- because that was all a programme needed. It was also the only thing
that could be reminded about, which made the store's ``station``, ``episode``
and ``other`` kinds a promise nothing kept.

This is the real dialog, and it is shared, so a reminder set on a station in
the browse tree and one set on a calendar programme are the same record with
the same fields:

* **When** -- a lead time before the thing, or a date and time of your own for
  something with no start of its own. A station has no "starts at"; "remind me
  about KFI at 6 p.m." does.
* **A note** (7.2) -- free text. A phone number to call in on, a reason, a
  message to yourself. It rides on the announcement.
* **Priority** (7.3) -- normal, or high. High is the *only* thing that can come
  through quiet hours, and even then only when quiet hours have been told to
  let reminders through at all: one switch is a preference, two agreeing is a
  decision. The label says so rather than making somebody find out.

Every control carries help text under the section-3 rule -- what it does, then
the misreading it prevents -- because a reminder is set once, in a hurry, and
the moment it is misunderstood is the moment it fails to arrive.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.radio import reminders
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Set a Reminder"

#: What the lead-time control offers when the thing has no start of its own.
#: "In an hour" is the useful shape for a station: you are not reminding
#: yourself *before* anything, you are asking to be told at a time.
_FROM_NOW: tuple[tuple[int, str], ...] = (
    (900, "In 15 minutes"),
    (1800, "In 30 minutes"),
    (3600, "In an hour"),
    (10800, "In 3 hours"),
    (86400, "Tomorrow, at this time"),
)


def ask(
    host: Any,
    parent: Any,
    *,
    title: str,
    kind: str,
    target: str,
    starts_at: datetime | None = None,
    note: str = "",
) -> Any:
    """Ask for the details and set the reminder. Returns it, or ``None``.

    *starts_at* is the moment the thing itself begins -- a programme's start.
    When it is ``None`` the thing has no start (a station, a saved item), so
    the question changes from "how long before?" to "when?", which is the same
    control reading differently rather than a second dialog.
    """
    import wx

    scheduled = starts_at is not None
    choices = (
        [label for _seconds, label in reminders.LEAD_CHOICES]
        if scheduled
        else [label for _seconds, label in _FROM_NOW]
    )

    dialog = wx.Dialog(parent, title=TITLE)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(wx.StaticText(dialog, label=f"Remind me about {title}"), 0, wx.ALL, 8)

    grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
    grid.AddGrowableCol(1, 1)

    grid.Add(wx.StaticText(dialog, label="&When:"), 0, wx.ALIGN_CENTER_VERTICAL)
    when = wx.Choice(dialog, choices=choices)
    # Opens on the listener's default (7.8) -- every reminder still asks, and
    # every one can differ; this only makes the usual answer one keystroke
    # shorter. The unscheduled list has its own shape, so it keeps its own
    # sensible middle rather than an index borrowed from the other list.
    when.SetSelection(_default_index(host) if scheduled else 2)
    _when_help = (
        (
            "How much warning you want before it starts. It changes when you "
            "are told, never what is played -- a reminder never starts, "
            "records or queues anything by itself."
        )
        if scheduled
        else (
            "When to tell you, counted from now. This one has no start time of "
            "its own, so the reminder is a time you choose rather than a "
            "warning before something."
        )
    )
    when.SetName(_when_help)
    when.SetHelpText(_when_help)
    grid.Add(when, 1, wx.EXPAND)

    grid.Add(wx.StaticText(dialog, label="&Note (optional):"), 0, wx.ALIGN_CENTER_VERTICAL)
    note_ctrl = wx.TextCtrl(dialog, value=note)
    _note_help = (
        "Anything you want said with the reminder -- a number to call in on, a "
        "reason, a message to yourself. It is spoken with the reminder and "
        "kept on this computer; leaving it empty is perfectly normal."
    )
    note_ctrl.SetName(_note_help)
    note_ctrl.SetHelpText(_note_help)
    grid.Add(note_ctrl, 1, wx.EXPAND)

    grid.Add(wx.StaticText(dialog, label="&Priority:"), 0, wx.ALIGN_CENTER_VERTICAL)
    priority = wx.Choice(dialog, choices=["Normal", "High"])
    priority.SetSelection(0)
    _priority_help = (
        "High is the only priority that can come through quiet hours -- and "
        "only when quiet hours have also been told to let reminders through. "
        "One switch is a preference; two agreeing is a decision. It changes "
        "nothing else: a high-priority reminder is not louder, sooner or "
        "repeated."
    )
    priority.SetName(_priority_help)
    priority.SetHelpText(_priority_help)
    grid.Add(priority, 1, wx.EXPAND)
    root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    buttons = dialog.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    dialog.SetSizerAndFit(root)

    try:
        shower = getattr(host, "_show_modal_dialog", None)
        answer = (
            shower(dialog, TITLE)
            if callable(shower)
            else dialog.ShowModal()  # dialog_button_contract: exempt
        )
        if answer != wx.ID_OK:
            return None
        index = max(0, when.GetSelection())
        chosen_note = note_ctrl.GetValue().strip()
        chosen_priority = (
            reminders.PRIORITY_HIGH if priority.GetSelection() == 1 else reminders.PRIORITY_NORMAL
        )
    finally:
        dialog.Destroy()

    from quill.core.paths import app_data_dir

    if scheduled:
        lead = reminders.LEAD_CHOICES[min(index, len(reminders.LEAD_CHOICES) - 1)][0]
        due = starts_at
    else:
        # No start of its own, so the "lead" is the delay and the due moment is
        # now plus it -- one control, two readings, rather than two dialogs.
        lead = 0
        due = datetime.now(UTC) + timedelta(seconds=_FROM_NOW[min(index, len(_FROM_NOW) - 1)][0])

    return reminders.add_reminder(
        app_data_dir(),
        title,
        due,
        kind=kind,
        target=target,
        note=chosen_note,
        lead_seconds=lead,
        priority=chosen_priority,
    )


def _default_index(host: Any) -> int:
    """Which lead time the control opens on, from Preferences.

    Falls back to the second row when there is no setting to read: an app
    without a history record still has to offer the dialog.
    """
    history = getattr(host, "_radio_history", None)
    wanted = getattr(history, "reminder_default_lead_seconds", None)
    for index, (offered, _label) in enumerate(reminders.LEAD_CHOICES):
        if offered == wanted:
            return index
    return 1


def spoken_confirmation(reminder: Any) -> str:
    """What to say once one is set. Says *when*, because that is the question."""
    when = reminders.spoken_when(reminder.fires_at)
    tail = " High priority." if reminder.priority == reminders.PRIORITY_HIGH else ""
    return f"Reminder set for {reminder.title}, {when}.{tail}"


__all__ = ["TITLE", "ask", "spoken_confirmation"]
