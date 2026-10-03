"""Change Schedule...: when one podcast, or every podcast, is checked (qc.md 5e).

One dialog for both levels. The Kind list comes first and the rows under it
change with it: a typed interval (minutes, hours or days -- typed, not chosen
from eight rows; the eight stay as quick picks), up to six times of day and
the days of the week, or the learned pattern in words with Pin and Reset.
Save confirms in the same words the Feed Check column uses, through
:func:`refresh_schedule.describe`, so the app never describes a schedule two
ways.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts import refresh_schedule as rs

__all__ = ["ScheduleDialog", "change_schedule"]

_QUICK = (
    (15, "15 minutes"),
    (30, "30 minutes"),
    (60, "1 hour"),
    (180, "3 hours"),
    (360, "6 hours"),
    (720, "12 hours"),
    (1440, "Once a day"),
)
_DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class ScheduleDialog:
    """``show()`` returns the chosen Schedule, or None."""

    def __init__(
        self,
        parent: Any,
        *,
        title: str,
        schedule: rs.Schedule,
        pattern: rs.Pattern | None,
        hint: rs.Hint,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        from quill.ui.dialog_contract import apply_modal_ids

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._pattern = pattern
        self._hint = hint
        self._schedule = schedule
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self.dialog, label="&Kind of schedule:"), 0, wx.LEFT | wx.TOP, 8)
        self._kind = wx.Choice(self.dialog, choices=[rs.KIND_LABELS[kind] for kind in rs.KINDS])
        self._kind.SetHelpText(
            "Manually only never checks on its own. Every so often checks on an "
            "interval you type. At set times checks at the times of day you list, "
            "on the days you choose. Around when it usually publishes learns the "
            "day and hour from the last twelve episodes and checks closely then. "
            "Follow the publisher's hint uses what the feed itself declares."
        )
        self._kind.SetSelection(rs.KINDS.index(schedule.kind))
        self._kind.Bind(wx.EVT_CHOICE, lambda _e: self._show_rows())
        root.Add(self._kind, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        # Every so often
        self._interval_label = wx.StaticText(self.dialog, label="&Every (number):")
        root.Add(self._interval_label, 0, wx.LEFT | wx.TOP, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        unit, amount = _split_minutes(schedule.minutes)
        self._amount = wx.SpinCtrl(self.dialog, min=1, max=10080, initial=amount)
        self._amount.SetHelpText(
            "How many of the unit beside it. Any number, not only the quick picks."
        )
        self._unit_label = wx.StaticText(self.dialog, label="U&nit:")
        self._unit = wx.Choice(self.dialog, choices=["minutes", "hours", "days"])
        self._unit.SetHelpText("Minutes, hours or days, for the number before it.")
        self._unit.SetSelection(unit)
        self._quick_label = wx.StaticText(self.dialog, label="&Quick pick:")
        self._quick = wx.Choice(
            self.dialog, choices=["(type your own)", *[label for _m, label in _QUICK]]
        )
        self._quick.SetHelpText(
            "The eight usual intervals, one keystroke each. It fills in the number and unit."
        )
        self._quick.SetSelection(0)
        self._quick.Bind(wx.EVT_CHOICE, lambda _e: self._apply_quick())
        row.Add(self._amount, 0, wx.RIGHT, 6)
        row.Add(self._unit_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(self._unit, 0, wx.RIGHT, 12)
        row.Add(self._quick_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(self._quick, 0)
        root.Add(row, 0, wx.LEFT | wx.RIGHT, 8)
        self._interval_row = row
        # At set times
        self._times_label = wx.StaticText(
            self.dialog, label="&Times of day, separated by commas (up to six, like 6:00, 18:00):"
        )
        root.Add(self._times_label, 0, wx.LEFT | wx.TOP, 8)
        self._times = wx.TextCtrl(self.dialog, value=", ".join(schedule.times))
        self._times.SetHelpText(
            "One to six times in 24-hour form, separated by commas. Blank means none chosen yet."
        )
        root.Add(self._times, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._days_label = wx.StaticText(
            self.dialog, label="On these &days (none chosen means every day):"
        )
        root.Add(self._days_label, 0, wx.LEFT | wx.TOP, 8)
        days = wx.BoxSizer(wx.HORIZONTAL)
        self._days: list[Any] = []
        for index, label in enumerate(_DAY_LABELS):
            box = wx.CheckBox(self.dialog, label=label)
            box.SetHelpText(f"Check on {label}. With no day checked, the times apply every day.")
            box.SetValue(index in schedule.days)
            days.Add(box, 0, wx.RIGHT, 6)
            self._days.append(box)
        root.Add(days, 0, wx.LEFT | wx.RIGHT, 8)
        self._days_row = days
        # Learned
        self._learned = wx.StaticText(self.dialog, label=self._learned_words())
        root.Add(self._learned, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        learned_row = wx.BoxSizer(wx.HORIZONTAL)
        self._pin = wx.Button(self.dialog, label="&Pin This Pattern")
        self._pin.SetHelpText(
            "Keeps the learned day and hour as they are now, so a one-off late episode "
            "cannot move them."
        )
        self._pin.Bind(wx.EVT_BUTTON, lambda _e: self._pin_pattern())
        self._reset = wx.Button(self.dialog, label="&Reset Learning")
        self._reset.SetHelpText("Forgets the pin and learns again from the newest episodes.")
        self._reset.Bind(wx.EVT_BUTTON, lambda _e: self._reset_pattern())
        learned_row.Add(self._pin, 0, wx.RIGHT, 6)
        learned_row.Add(self._reset, 0)
        root.Add(learned_row, 0, wx.LEFT | wx.RIGHT, 8)
        self._learned_row = learned_row
        # Publisher
        self._publisher = wx.StaticText(
            self.dialog, label=rs.describe(rs.Schedule(rs.PUBLISHER), hint=hint)
        )
        root.Add(self._publisher, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        # Buttons
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        ok = wx.Button(self.dialog, wx.ID_OK, label="Save")
        ok.SetHelpText("Saves this schedule and says it back in one sentence.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Closes this window without saving; nothing you changed here is kept.")
        buttons.Add(ok, 0, wx.RIGHT, 6)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(
            self.dialog, affirmative_id=wx.ID_OK, affirmative_label="Save", cancel_id=wx.ID_CANCEL
        )
        self._pinned = schedule.pinned
        self._show_rows()
        self.dialog.SetSize((620, 460))
        self._kind.SetFocus()

    # -- rows per kind ----------------------------------------------------------- #

    def _current_kind(self) -> str:
        return rs.KINDS[max(0, self._kind.GetSelection())]

    def _show_rows(self) -> None:
        kind = self._current_kind()
        interval = kind == rs.INTERVAL
        times = kind == rs.TIMES
        learned = kind == rs.LEARNED
        for control in (
            self._interval_label,
            self._amount,
            self._unit_label,
            self._unit,
            self._quick_label,
            self._quick,
        ):
            control.Show(interval)
        for control in (self._times_label, self._times, self._days_label, *self._days):
            control.Show(times)
        for control in (self._learned, self._pin, self._reset):
            control.Show(learned)
        self._publisher.Show(kind == rs.PUBLISHER)
        self.dialog.Layout()

    def _apply_quick(self) -> None:
        index = self._quick.GetSelection() - 1
        if index < 0:
            return
        minutes = _QUICK[index][0]
        unit, amount = _split_minutes(minutes)
        self._unit.SetSelection(unit)
        self._amount.SetValue(amount)

    def _learned_words(self) -> str:
        if self._schedule.pinned is not None:
            return rs.describe(rs.Schedule(rs.LEARNED, pinned=self._schedule.pinned))
        return rs.describe(rs.Schedule(rs.LEARNED), pattern=self._pattern)

    def _pin_pattern(self) -> None:
        if self._pattern is None:
            self._announce("Nothing learned yet to pin; it needs three episodes that agree.")
            return
        self._pinned = (
            self._pattern.weekday if self._pattern.weekday is not None else 0,
            self._pattern.hour,
        )
        self._schedule = rs.Schedule(rs.LEARNED, pinned=self._pinned)
        self._learned.SetLabel(self._learned_words())
        self._announce(self._learned.GetLabel())

    def _reset_pattern(self) -> None:
        self._pinned = None
        self._schedule = rs.Schedule(rs.LEARNED)
        self._learned.SetLabel(self._learned_words())
        self._announce(self._learned.GetLabel())

    # -- the answer --------------------------------------------------------------------- #

    def _read(self) -> rs.Schedule | None:
        kind = self._current_kind()
        if kind == rs.INTERVAL:
            unit = (1, 60, 1440)[max(0, self._unit.GetSelection())]
            return rs.Schedule(rs.INTERVAL, max(5, int(self._amount.GetValue()) * unit))
        if kind == rs.TIMES:
            times = tuple(
                part.strip() for part in self._times.GetValue().split(",") if part.strip()
            )
            decoded = rs.decode(rs.encode(rs.Schedule(rs.TIMES, times=times[:6])))
            if decoded is None or not decoded.times:
                self._announce("Type at least one time of day, like 6:00.")
                return None
            days = tuple(index for index, box in enumerate(self._days) if box.GetValue())
            return rs.Schedule(rs.TIMES, times=decoded.times, days=days)
        if kind == rs.LEARNED:
            return rs.Schedule(rs.LEARNED, pinned=self._pinned)
        return rs.Schedule(kind)

    def show(self) -> rs.Schedule | None:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        try:
            while True:
                answer = show_modal_dialog(
                    self.dialog, self.dialog.GetTitle(), announce=self._announce
                )
                if answer != self._wx.ID_OK:
                    return None
                schedule = self._read()
                if schedule is not None:
                    return schedule
        finally:
            self.dialog.Destroy()


def _split_minutes(minutes: int) -> tuple[int, int]:
    """(unit index, amount): the largest unit that divides evenly."""
    if minutes % 1440 == 0:
        return 2, minutes // 1440
    if minutes % 60 == 0:
        return 1, minutes // 60
    return 0, minutes


def change_schedule(host: Any, show: Any) -> bool:
    """Change Schedule... on a podcast (or, with None, the shared default)."""
    from quill.core.podcasts import schedule_policy

    library = host._podcast_library
    title = f"Schedule for {show.title}" if show is not None else "Schedule for Every Podcast"
    dialog = ScheduleDialog(
        host.frame,
        title=title,
        schedule=schedule_policy.schedule_for(library, show),
        pattern=schedule_policy.pattern_for(show) if show is not None else None,
        hint=schedule_policy.hint_for(library, show) if show is not None else rs.Hint(),
        announce=host._announce,
    )
    schedule = dialog.show()
    if schedule is None:
        return False
    schedule_policy.set_schedule(library, show, schedule)
    host._save_podcast_library()
    who = show.title if show is not None else "Every podcast"
    said = schedule_policy.describe_for(library, show)
    host._announce(f"{who} now checks: {said[0].lower() + said[1:]}")
    return True
