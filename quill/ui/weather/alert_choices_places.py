"""The Places page of Alert Choices: which saved places are watched, and when.

A plain list box whose rows say their own state ("Home, watched", "Cabin, not
watched, switched off"), so a screen reader reads each row as ordinary text with
nothing to find in a second column. Space toggles the focused place. Below it:
Watch All, Watch None, Invert, snooze, watch until, a schedule, and groups.

The rules live in ``quill.core.weather.place_watch``; this page only edits an
in-memory copy (``self._muted``, ``self._watches``) that Save writes out.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from quill.core.weather import alert_rules as ar
from quill.core.weather import place_watch
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.dpi import dip_size

_SAME = "Same as everywhere"
_ENDS = "End the snooze"
_PRESETS = ("everything", "essentials", "safety")


class AlertChoicesPlaces:
    _wx: Any
    _book: Any
    _places: list[tuple[str, str]]
    _muted: set[str]
    _watches: place_watch.PlaceWatches
    _place_rules: dict[str, ar.RuleSet]

    def _announce(self, message: str) -> None: ...
    def _button(self, parent: Any, label: str, help_text: str, handler: Any) -> Any: ...
    def _place_control(
        self, parent: Any, sizer: Any, label: str, control: Any, name: str
    ) -> None: ...
    def _collect_general(self) -> ar.RuleSet: ...

    @staticmethod
    def _now() -> datetime:
        return datetime.now().astimezone()

    def _build_places(self) -> Any:
        wx = self._wx
        page = wx.ScrolledWindow(self._book)
        page.SetScrollRate(0, 12)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(
            wx.StaticText(
                page,
                label="Every saved place is watched unless you switch it off. Switching a "
                "place off keeps it saved. Press Space to switch the selected place.",
            ),
            0,
            wx.ALL,
            8,
        )
        self._place_list = wx.ListBox(page, size=dip_size(page, 520, 130))
        set_accessible_name(self._place_list, "Saved places and whether each is watched")
        self._place_list.SetHelpText(
            "Your saved places. Each row says whether the place is watched, snoozed, outside "
            "its schedule or switched off. Space switches the selected place on or off."
        )
        self._place_list.Bind(wx.EVT_LISTBOX, lambda _e: self._place_selected())
        self._place_list.Bind(wx.EVT_KEY_DOWN, self._on_place_key)
        sizer.Add(self._place_list, 1, wx.EXPAND | wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, handler in (
            ("Watch &all", "Watch every saved place.", self._watch_all),
            ("Watch &none", "Switch every saved place off. They stay saved.", self._watch_none),
            ("&Invert", "Swap which places are watched and which are off.", self._invert),
            (
                "&Switch this place",
                "Watch or stop watching the selected place.",
                self._toggle_place,
            ),
        ):
            row.Add(self._button(page, label, help_text, handler), 0, wx.RIGHT, 6)
        sizer.Add(row, 0, wx.LEFT | wx.BOTTOM, 8)

        self._snooze = wx.Choice(page, choices=[*place_watch.SNOOZE_CHOICES, _ENDS])
        self._snooze.SetHelpText(
            "A snoozed place is still checked, but stays quiet until the snooze ends. An "
            "Extreme alert still breaks through unless you turned that off in Quiet hours."
        )
        self._place_control(
            page, sizer, "S&nooze the selected place:", self._snooze, "Snooze the selected place"
        )
        self._snooze.Bind(wx.EVT_CHOICE, lambda _e: self._apply_snooze())
        self._until = wx.TextCtrl(page)
        self._until.SetHelpText(
            "Watch a switched-off place for a while, such as a trip. It stops by itself at "
            "that time and tells you once."
        )
        self._place_control(
            page,
            sizer,
            "Watch the selected place &until (like 2026-12-03 18:00, empty to clear):",
            self._until,
            "Watch the selected place until",
        )
        sizer.Add(
            self._button(page, "Set watch &until", "Apply the time above.", self._apply_until),
            0,
            wx.LEFT,
            8,
        )
        self._schedule = wx.TextCtrl(page)
        self._schedule.SetHelpText(
            "Outside its schedule a place is quiet, like a snooze. Days like Mon-Fri or "
            "Sat,Sun, then hours like 08:00-18:00."
        )
        self._place_control(
            page,
            sizer,
            "Sche&dule for the selected place (like Mon-Fri 08:00-18:00, empty for always):",
            self._schedule,
            "Schedule for the selected place",
        )
        sizer.Add(
            self._button(page, "Set sche&dule", "Apply the schedule above.", self._apply_schedule),
            0,
            wx.LEFT,
            8,
        )
        self._groups = wx.TextCtrl(page)
        self._groups.SetHelpText(
            "Names that let you watch or stop watching several places together."
        )
        self._place_control(
            page,
            sizer,
            "&Groups for the selected place (separated by commas, like Family, Travel):",
            self._groups,
            "Groups for the selected place",
        )
        sizer.Add(
            self._button(page, "Set &groups", "Apply the groups above.", self._apply_groups),
            0,
            wx.LEFT,
            8,
        )
        self._group_pick = wx.Choice(page)
        self._group_pick.SetHelpText("Pick a group, then use the buttons below.")
        self._place_control(
            page,
            sizer,
            "Watch or stop watching a whole group:",
            self._group_pick,
            "Group to change",
        )
        grow = wx.BoxSizer(wx.HORIZONTAL)
        grow.Add(
            self._button(
                page,
                "Watch the g&roup",
                "Watch every place in the group.",
                lambda: self._group_watch(True),
            ),
            0,
            wx.RIGHT,
            6,
        )
        grow.Add(
            self._button(
                page,
                "Stop watching the gro&up",
                "Switch off every place in the group.",
                lambda: self._group_watch(False),
            )
        )
        sizer.Add(grow, 0, wx.LEFT | wx.BOTTOM, 8)
        self._place_choice = wx.Choice(
            page, choices=[_SAME, *[ar.PRESET_LABELS[p] for p in _PRESETS]]
        )
        self._place_choice.SetHelpText(
            "Same as everywhere uses the choices on the first page. The others give this "
            "place its own ready-made choices."
        )
        self._place_control(
            page,
            sizer,
            "Alert choices for the selected &place:",
            self._place_choice,
            "Alert choices for the selected place",
        )
        self._place_choice.Bind(wx.EVT_CHOICE, lambda _e: self._place_choice_changed())
        page.SetSizer(sizer)
        return page

    # -- rows ------------------------------------------------------------------------

    def _fill_places(self, keep: int = 0) -> None:
        now = self._now()
        rows = [
            place_watch.row_text(pid, label, self._muted, self._watches, now)
            for pid, label in self._places
        ]
        self._place_list.Set(rows)
        self._group_pick.Set(self._watches.groups())
        if rows:
            self._place_list.SetSelection(max(0, min(keep, len(rows) - 1)))
            self._place_selected()

    def _selected_place(self) -> str | None:
        i = self._place_list.GetSelection()
        return self._places[i][0] if 0 <= i < len(self._places) else None

    def _selected_rule(self) -> place_watch.PlaceRule | None:
        pid = self._selected_place()
        return self._watches.rule(pid) if pid else None

    def _place_selected(self) -> None:
        pid = self._selected_place()
        if pid is None:
            return
        rule = self._watches.rules.get(pid)
        self._until.SetValue(
            datetime.fromtimestamp(rule.until).strftime("%Y-%m-%d %H:%M")
            if rule and rule.until
            else ""
        )
        self._schedule.SetValue(_schedule_text(rule))
        self._groups.SetValue(", ".join(rule.groups) if rule else "")
        rules = self._place_rules.get(pid)
        preset = rules.selection.preset if rules else ""
        self._place_choice.SetSelection(1 + _PRESETS.index(preset) if preset in _PRESETS else 0)

    def _on_place_key(self, event: Any) -> None:
        if event.GetKeyCode() == self._wx.WXK_SPACE:
            self._toggle_place()
        else:
            event.Skip()

    def _said(self) -> None:
        self._announce(
            place_watch.summary_sentence(self._places, self._muted, self._watches, self._now())
        )

    def _refresh(self) -> None:
        self._fill_places(max(0, self._place_list.GetSelection()))
        self._said()

    # -- changes ------------------------------------------------------------------------

    def _watch_all(self) -> None:
        self._muted = place_watch.watch_all(self._muted)
        self._refresh()

    def _watch_none(self) -> None:
        self._muted = place_watch.watch_none([p for p, _l in self._places])
        self._refresh()

    def _invert(self) -> None:
        self._muted = place_watch.invert([p for p, _l in self._places], self._muted)
        self._refresh()

    def _toggle_place(self) -> None:
        pid = self._selected_place()
        if pid is None:
            return
        self._muted ^= {pid}
        self._refresh()

    def _apply_snooze(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            return
        choice = self._snooze.GetStringSelection()
        if choice == _ENDS:
            place_watch.end_snooze(rule)
        else:
            place_watch.snooze(rule, choice, self._now())
        self._refresh()

    def _apply_until(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            return
        try:
            when = place_watch.parse_until(self._until.GetValue(), self._now())
        except ValueError as error:
            self._announce(str(error))
            self._until.SetFocus()
            return
        place_watch.set_watch_until(rule, when)
        if when is not None:
            self._muted.add(self._selected_place() or "")  # a temporary watch of an off place
        self._refresh()

    def _apply_schedule(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            return
        try:
            rule.schedule = place_watch.parse_schedule(self._schedule.GetValue())
        except ValueError as error:
            self._announce(str(error))
            self._schedule.SetFocus()
            return
        self._refresh()

    def _apply_groups(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            return
        names = [n.strip() for n in self._groups.GetValue().split(",") if n.strip()]
        rule.groups = list(dict.fromkeys(names))[:10]
        self._refresh()

    def _group_watch(self, watched: bool) -> None:
        group = self._group_pick.GetStringSelection()
        if not group:
            self._announce("Choose a group first.")
            return
        self._muted = place_watch.set_group(self._muted, self._watches, group, watched)
        self._refresh()

    def _place_choice_changed(self) -> None:
        pid = self._selected_place()
        if pid is None:
            return
        i = self._place_choice.GetSelection()
        if i == 0:
            self._place_rules.pop(pid, None)
        else:
            self._place_rules[pid] = ar.RuleSet(
                ar.Selection(_PRESETS[i - 1]), self._collect_general().delivery
            )
        self._fill_places(self._place_list.GetSelection())


def _schedule_text(rule: place_watch.PlaceRule | None) -> str:
    return rule.schedule.as_text() if rule is not None and rule.schedule is not None else ""
