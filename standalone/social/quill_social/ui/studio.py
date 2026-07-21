"""Accessible studio dialogs over the publishing services (PRD section 18).

These wx.Dialog surfaces expose already-built, already-tested services -- the
publishing calendar (PRD 18.5), queue schedules (PRD 18.2, 18.4), the approval
workflow (PRD 18.8), and the local draft store (PRD 15, 16) -- without adding any
new domain logic. Every control carries a visible label and an accessible name,
data tables are ``wx.ListCtrl`` report lists with named columns, and every action
is reachable from the keyboard. The dialogs are thin: they read and write the
store and call into ``quill_social.services`` for all reasoning.
"""

from __future__ import annotations

import wx

from quill_social.model import now_ms
from quill_social.services import approvals as approvals_svc
from quill_social.services import calendar as calendar_svc
from quill_social.services import queue_schedule as qsched_svc
from quill_social.services.approvals import ApprovalError, ApprovalRecord
from quill_social.services.queue_schedule import (
    BlackoutWindow,
    QueueSchedule,
    Slot,
)

_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_AGENDA_VIEWS = ("Agenda", "Day", "Week", "Month")


def _add_row(ctrl: wx.ListCtrl, values: list[str]) -> int:
    """Append one row of column strings to a report ``ListCtrl``; return index."""
    idx = ctrl.InsertItem(ctrl.GetItemCount(), values[0])
    for col, text in enumerate(values[1:], start=1):
        ctrl.SetItem(idx, col, text)
    return idx


# -- drafts -------------------------------------------------------------------


class DraftsDialog(wx.Dialog):
    """List and manage saved drafts (PRD 15, 16).

    Exposes :attr:`chosen_draft_id`: when the user picks Edit it is set to the
    selected draft id so the caller can open the composer on it.
    """

    def __init__(self, parent, store):
        super().__init__(
            parent,
            title="Drafts",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._store = store
        self.chosen_draft_id: str = ""

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(wx.StaticText(self, label="Saved drafts:"), 0, wx.LEFT | wx.TOP, 8)

        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetName("Drafts")
        self.list.InsertColumn(0, "Name", width=160)
        self.list.InsertColumn(1, "Preview", width=320)
        self.list.InsertColumn(2, "Targets", width=80)
        self.list.InsertColumn(3, "Updated", width=140)
        outer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.edit_btn = wx.Button(self, label="&Edit")
        self.edit_btn.SetName("Edit draft")
        self.delete_btn = wx.Button(self, label="&Delete")
        self.delete_btn.SetName("Delete draft")
        close_btn = wx.Button(self, wx.ID_CANCEL, label="&Close")
        close_btn.SetName("Close")
        for b in (self.edit_btn, self.delete_btn, close_btn):
            btns.Add(b, 0, wx.RIGHT, 6)
        outer.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizer(outer)
        self.SetSize((760, 420))

        self.edit_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_edit())
        self.delete_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_delete())
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._on_edit())

        self._drafts: list = []
        self._reload()

    def _reload(self) -> None:
        self._drafts = self._store.list_drafts()
        self.list.DeleteAllItems()
        for draft in self._drafts:
            name = draft.name or "(untitled)"
            preview = draft.text.strip().replace("\n", " ")[:80] or "(empty)"
            updated = _fmt_ms_utc(draft.updated)
            _add_row(self.list, [name, preview, str(len(draft.targets)), updated])
        if self._drafts:
            self.list.Select(0)
            self.list.Focus(0)

    def _selected_draft(self):
        idx = self.list.GetFirstSelected()
        if idx < 0 or idx >= len(self._drafts):
            return None
        return self._drafts[idx]

    def _on_edit(self) -> None:
        draft = self._selected_draft()
        if draft is None:
            wx.MessageBox("Select a draft first.", "Drafts", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.chosen_draft_id = draft.draft_id
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    def _on_delete(self) -> None:
        draft = self._selected_draft()
        if draft is None:
            wx.MessageBox("Select a draft first.", "Drafts", wx.OK | wx.ICON_INFORMATION, self)
            return
        self._store.delete_draft(draft.draft_id)
        self._reload()


# -- agenda / calendar --------------------------------------------------------


class AgendaDialog(wx.Dialog):
    """Accessible publishing calendar over publication plans (PRD 18.5).

    The agenda list is the accessibility baseline; a view selector switches
    between the flat agenda and day/week/month groupings, and scheduling
    conflicts are surfaced as plain text.
    """

    def __init__(self, parent, store):
        super().__init__(
            parent,
            title="Publishing calendar",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._store = store

        outer = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(
            wx.StaticText(self, label="View:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.view = wx.Choice(self, choices=list(_AGENDA_VIEWS))
        self.view.SetName("Calendar view")
        self.view.SetSelection(0)
        top.Add(self.view, 0, wx.RIGHT, 12)
        top.Add(
            wx.StaticText(self, label="Minimum spacing (minutes):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.spacing = wx.SpinCtrl(self, min=0, max=1440, initial=30)
        self.spacing.SetName("Minimum spacing minutes")
        top.Add(self.spacing, 0)
        outer.Add(top, 0, wx.ALL, 8)

        outer.Add(wx.StaticText(self, label="Agenda:"), 0, wx.LEFT, 8)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetName("Agenda")
        self.list.InsertColumn(0, "Group", width=110)
        self.list.InsertColumn(1, "When", width=170)
        self.list.InsertColumn(2, "Account", width=110)
        self.list.InsertColumn(3, "Network", width=80)
        self.list.InsertColumn(4, "Campaign", width=110)
        self.list.InsertColumn(5, "State", width=90)
        self.list.InsertColumn(6, "Approval", width=90)
        self.list.InsertColumn(7, "Preview", width=220)
        outer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)

        outer.Add(wx.StaticText(self, label="Conflicts:"), 0, wx.LEFT, 8)
        self.conflicts = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 90),
        )
        self.conflicts.SetName("Scheduling conflicts")
        outer.Add(self.conflicts, 0, wx.EXPAND | wx.ALL, 8)

        close_btn = wx.Button(self, wx.ID_CANCEL, label="&Close")
        close_btn.SetName("Close")
        outer.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizer(outer)
        self.SetSize((900, 520))

        self.view.Bind(wx.EVT_CHOICE, lambda _e: self._refresh())
        self.spacing.Bind(wx.EVT_SPINCTRL, lambda _e: self._refresh())

        self._refresh()

    def set_view(self, name: str) -> None:
        """Programmatically select a view by name and refresh (test hook)."""
        if name in _AGENDA_VIEWS:
            self.view.SetSelection(_AGENDA_VIEWS.index(name))
            self._refresh()

    def _refresh(self) -> None:
        plans = self._store.list_plans()
        drafts = {d.draft_id: d for d in self._store.list_drafts()}
        campaigns = {c.campaign_id: c for c in self._store.list_campaigns()}
        spacing = self.spacing.GetValue()
        entries = calendar_svc.agenda(
            plans,
            now=now_ms(),
            drafts=drafts,
            campaigns=campaigns,
            min_spacing_min=spacing,
        )
        by_id = {e.plan_id: e for e in entries}

        view = _AGENDA_VIEWS[self.view.GetSelection()]
        if view == "Day":
            groups = calendar_svc.group_by_day(plans)
        elif view == "Week":
            groups = calendar_svc.group_by_week(plans)
        elif view == "Month":
            groups = calendar_svc.group_by_month(plans)
        else:
            groups = None

        self.list.DeleteAllItems()
        if groups is None:
            for entry in entries:
                self._add_entry("", entry)
        else:
            for key, group_plans in groups.items():
                for plan in group_plans:
                    entry = by_id.get(plan.plan_id)
                    if entry is not None:
                        self._add_entry(key, entry)

        pairs = calendar_svc.conflicts(plans, spacing)
        if not pairs:
            self.conflicts.SetValue("No scheduling conflicts.")
        else:
            lines = [f"{len(pairs)} conflict(s) at minimum spacing {spacing} minutes:"]
            for pair in pairs:
                lines.append(
                    f"account {pair.first.account_id}: plans "
                    f"{pair.first.plan_id} and {pair.second.plan_id}, "
                    f"gap {pair.gap_min} minutes"
                )
            self.conflicts.SetValue("\n".join(lines))

    def _add_entry(self, group: str, entry) -> None:
        _add_row(
            self.list,
            [
                group,
                entry.when_text,
                entry.account_id or "(none)",
                entry.network or "(unknown)",
                entry.campaign or "(none)",
                entry.state,
                entry.approval_state,
                entry.preview,
            ],
        )


# -- queue schedule -----------------------------------------------------------


class QueueScheduleDialog(wx.Dialog):
    """Create or edit a posting queue schedule (PRD 18.2, 18.4).

    Captures the weekly slots, spacing, daily limit, and blackout windows, then
    persists the schedule to the document store and previews the next computed
    posting slots as confirmation.
    """

    def __init__(self, parent, store, schedule: QueueSchedule | None = None):
        super().__init__(
            parent,
            title="Queue schedule",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._store = store
        self.schedule: QueueSchedule = schedule or QueueSchedule(name="New queue")

        outer = wx.BoxSizer(wx.VERTICAL)

        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(
            wx.StaticText(self, label="Name:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.name = wx.TextCtrl(self, value=self.schedule.name)
        self.name.SetName("Schedule name")
        name_row.Add(self.name, 1, wx.RIGHT, 12)
        name_row.Add(
            wx.StaticText(self, label="Time zone (IANA):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.timezone = wx.TextCtrl(self, value=self.schedule.timezone or "UTC")
        self.timezone.SetName("Time zone")
        name_row.Add(self.timezone, 1)
        outer.Add(name_row, 0, wx.EXPAND | wx.ALL, 8)

        limits = wx.BoxSizer(wx.HORIZONTAL)
        limits.Add(
            wx.StaticText(self, label="Minimum spacing (minutes):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.min_spacing = wx.SpinCtrl(
            self, min=0, max=10080, initial=self.schedule.min_spacing_min
        )
        self.min_spacing.SetName("Minimum spacing minutes")
        limits.Add(self.min_spacing, 0, wx.RIGHT, 12)
        limits.Add(
            wx.StaticText(self, label="Daily limit:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.daily_limit = wx.SpinCtrl(
            self, min=0, max=100, initial=self.schedule.daily_limit
        )
        self.daily_limit.SetName("Daily limit")
        limits.Add(self.daily_limit, 0)
        outer.Add(limits, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Slots.
        outer.Add(wx.StaticText(self, label="Weekly slots:"), 0, wx.LEFT, 8)
        self.slots_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.slots_list.SetName("Weekly slots")
        self.slots_list.InsertColumn(0, "Weekday", width=120)
        self.slots_list.InsertColumn(1, "Time", width=100)
        outer.Add(self.slots_list, 1, wx.EXPAND | wx.ALL, 8)

        slot_row = wx.BoxSizer(wx.HORIZONTAL)
        slot_row.Add(
            wx.StaticText(self, label="Weekday:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.slot_weekday = wx.Choice(self, choices=list(_WEEKDAYS))
        self.slot_weekday.SetName("Slot weekday")
        self.slot_weekday.SetSelection(0)
        slot_row.Add(self.slot_weekday, 0, wx.RIGHT, 12)
        slot_row.Add(
            wx.StaticText(self, label="Hour:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.slot_hour = wx.SpinCtrl(self, min=0, max=23, initial=9)
        self.slot_hour.SetName("Slot hour")
        slot_row.Add(self.slot_hour, 0, wx.RIGHT, 12)
        slot_row.Add(
            wx.StaticText(self, label="Minute:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.slot_minute = wx.SpinCtrl(self, min=0, max=59, initial=0)
        self.slot_minute.SetName("Slot minute")
        slot_row.Add(self.slot_minute, 0, wx.RIGHT, 12)
        self.add_slot_btn = wx.Button(self, label="&Add slot")
        self.add_slot_btn.SetName("Add slot")
        slot_row.Add(self.add_slot_btn, 0, wx.RIGHT, 6)
        self.remove_slot_btn = wx.Button(self, label="&Remove slot")
        self.remove_slot_btn.SetName("Remove slot")
        slot_row.Add(self.remove_slot_btn, 0)
        outer.Add(slot_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Blackout windows.
        outer.Add(wx.StaticText(self, label="Blackout windows:"), 0, wx.LEFT, 8)
        self.blackout_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.blackout_list.SetName("Blackout windows")
        self.blackout_list.InsertColumn(0, "Start (ms UTC)", width=140)
        self.blackout_list.InsertColumn(1, "End (ms UTC)", width=140)
        self.blackout_list.InsertColumn(2, "Reason", width=200)
        outer.Add(self.blackout_list, 0, wx.EXPAND | wx.ALL, 8)

        bo_row = wx.BoxSizer(wx.HORIZONTAL)
        bo_row.Add(
            wx.StaticText(self, label="Start ms:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.bo_start = wx.TextCtrl(self, value="0")
        self.bo_start.SetName("Blackout start ms")
        bo_row.Add(self.bo_start, 0, wx.RIGHT, 12)
        bo_row.Add(
            wx.StaticText(self, label="End ms:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.bo_end = wx.TextCtrl(self, value="0")
        self.bo_end.SetName("Blackout end ms")
        bo_row.Add(self.bo_end, 0, wx.RIGHT, 12)
        bo_row.Add(
            wx.StaticText(self, label="Reason:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.bo_reason = wx.TextCtrl(self)
        self.bo_reason.SetName("Blackout reason")
        bo_row.Add(self.bo_reason, 1, wx.RIGHT, 12)
        self.add_bo_btn = wx.Button(self, label="Add &blackout")
        self.add_bo_btn.SetName("Add blackout")
        bo_row.Add(self.add_bo_btn, 0, wx.RIGHT, 6)
        self.remove_bo_btn = wx.Button(self, label="Remove bl&ackout")
        self.remove_bo_btn.SetName("Remove blackout")
        bo_row.Add(self.remove_bo_btn, 0)
        outer.Add(bo_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Preview + save.
        outer.Add(wx.StaticText(self, label="Next slots preview:"), 0, wx.LEFT, 8)
        self.preview = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 90),
        )
        self.preview.SetName("Next slots preview")
        outer.Add(self.preview, 0, wx.EXPAND | wx.ALL, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = wx.Button(self, label="&Save schedule")
        self.save_btn.SetName("Save schedule")
        close_btn = wx.Button(self, wx.ID_CANCEL, label="&Close")
        close_btn.SetName("Close")
        btns.Add(self.save_btn, 0, wx.RIGHT, 6)
        btns.Add(close_btn, 0)
        outer.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizer(outer)
        self.SetSize((820, 720))

        self.add_slot_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_add_slot())
        self.remove_slot_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove_slot())
        self.add_bo_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_add_blackout())
        self.remove_bo_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove_blackout())
        self.save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save())

        self._reload_slots()
        self._reload_blackouts()
        self._refresh_preview()

    # -- slots ---------------------------------------------------------------

    def _reload_slots(self) -> None:
        self.slots_list.DeleteAllItems()
        for slot in self.schedule.slots:
            weekday = _WEEKDAYS[slot.weekday % 7]
            _add_row(self.slots_list, [weekday, f"{slot.hour:02d}:{slot.minute:02d}"])

    def _on_add_slot(self) -> None:
        slot = Slot(
            weekday=self.slot_weekday.GetSelection(),
            hour=self.slot_hour.GetValue(),
            minute=self.slot_minute.GetValue(),
        )
        self.schedule.slots.append(slot)
        self._reload_slots()
        self._refresh_preview()

    def _on_remove_slot(self) -> None:
        idx = self.slots_list.GetFirstSelected()
        if 0 <= idx < len(self.schedule.slots):
            del self.schedule.slots[idx]
            self._reload_slots()
            self._refresh_preview()

    # -- blackout windows ----------------------------------------------------

    def _reload_blackouts(self) -> None:
        self.blackout_list.DeleteAllItems()
        for window in self.schedule.blackout_windows:
            _add_row(
                self.blackout_list,
                [str(window.start_ms), str(window.end_ms), window.reason],
            )

    def _on_add_blackout(self) -> None:
        try:
            start = int(self.bo_start.GetValue().strip() or "0")
            end = int(self.bo_end.GetValue().strip() or "0")
        except ValueError:
            wx.MessageBox(
                "Blackout start and end must be integer milliseconds.",
                "Queue schedule",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        self.schedule.blackout_windows.append(
            BlackoutWindow(start_ms=start, end_ms=end, reason=self.bo_reason.GetValue())
        )
        self._reload_blackouts()
        self._refresh_preview()

    def _on_remove_blackout(self) -> None:
        idx = self.blackout_list.GetFirstSelected()
        if 0 <= idx < len(self.schedule.blackout_windows):
            del self.schedule.blackout_windows[idx]
            self._reload_blackouts()
            self._refresh_preview()

    # -- build / persist -----------------------------------------------------

    def _apply_fields(self) -> None:
        self.schedule.name = self.name.GetValue().strip() or "New queue"
        self.schedule.timezone = self.timezone.GetValue().strip() or "UTC"
        self.schedule.min_spacing_min = self.min_spacing.GetValue()
        self.schedule.daily_limit = self.daily_limit.GetValue()

    def _refresh_preview(self) -> None:
        self._apply_fields()
        if not self.schedule.slots:
            self.preview.SetValue("Add at least one slot to preview posting times.")
            return
        now = now_ms()
        horizon = now + 14 * 86_400_000
        slots = qsched_svc.slots_between(self.schedule, now, horizon)
        first = qsched_svc.next_slot(self.schedule, now, [], now=now)
        lines: list[str] = []
        if first is None:
            lines.append("No available slot in the next 366 days.")
        else:
            lines.append(f"Next available slot: {_fmt_ms_utc(first)} UTC")
        lines.append(f"{len(slots)} slot(s) in the next 14 days:")
        for ms in slots[:6]:
            lines.append(f"  {_fmt_ms_utc(ms)} UTC")
        self.preview.SetValue("\n".join(lines))

    def _on_save(self) -> None:
        self._apply_fields()
        qsched_svc.save(self._store, self.schedule)
        self._refresh_preview()
        wx.MessageBox(
            f"Saved schedule '{self.schedule.name}'.",
            "Queue schedule",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )


# -- approvals ----------------------------------------------------------------


class ApprovalsDialog(wx.Dialog):
    """Review approval records and drive review-side transitions (PRD 18.8).

    Lists persisted approval records with their state and audit trail. The
    Request approval, Approve, and Request changes actions are gated by the
    selected role via ``approvals.can_perform`` and append audit entries.
    """

    def __init__(self, parent, store):
        super().__init__(
            parent,
            title="Approvals",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._store = store
        self._records: list[ApprovalRecord] = []

        outer = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(
            wx.StaticText(self, label="Acting as role:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.role = wx.Choice(self, choices=list(approvals_svc.ROLES))
        self.role.SetName("Acting role")
        self.role.SetSelection(0)
        top.Add(self.role, 0, wx.RIGHT, 12)
        top.Add(
            wx.StaticText(self, label="Draft:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.draft = wx.Choice(self, choices=[])
        self.draft.SetName("Draft")
        top.Add(self.draft, 1)
        outer.Add(top, 0, wx.EXPAND | wx.ALL, 8)

        outer.Add(wx.StaticText(self, label="Approval records:"), 0, wx.LEFT, 8)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetName("Approval records")
        self.list.InsertColumn(0, "Record", width=160)
        self.list.InsertColumn(1, "Draft", width=160)
        self.list.InsertColumn(2, "State", width=140)
        self.list.InsertColumn(3, "Audit steps", width=100)
        outer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)

        outer.Add(wx.StaticText(self, label="Audit trail:"), 0, wx.LEFT, 8)
        self.audit = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 120),
        )
        self.audit.SetName("Audit trail")
        outer.Add(self.audit, 0, wx.EXPAND | wx.ALL, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.request_btn = wx.Button(self, label="&Request approval")
        self.request_btn.SetName("Request approval")
        self.approve_btn = wx.Button(self, label="&Approve")
        self.approve_btn.SetName("Approve")
        self.changes_btn = wx.Button(self, label="Request &changes")
        self.changes_btn.SetName("Request changes")
        close_btn = wx.Button(self, wx.ID_CANCEL, label="&Close")
        close_btn.SetName("Close")
        for b in (self.request_btn, self.approve_btn, self.changes_btn, close_btn):
            btns.Add(b, 0, wx.RIGHT, 6)
        outer.Add(btns, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizer(outer)
        self.SetSize((820, 560))

        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self._show_audit())
        self.request_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_request())
        self.approve_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_approve())
        self.changes_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_changes())

        self._reload_drafts()
        self._reload_records()

    # -- data ----------------------------------------------------------------

    def _reload_drafts(self) -> None:
        self._drafts = self._store.list_drafts()
        labels = [f"{d.name or '(untitled)'} [{d.draft_id}]" for d in self._drafts]
        self.draft.Set(labels)
        if self._drafts:
            self.draft.SetSelection(0)

    def _reload_records(self) -> None:
        self._records = approvals_svc.load_all(self._store)
        self.list.DeleteAllItems()
        for record in self._records:
            _add_row(
                self.list,
                [
                    record.record_id,
                    record.draft_id or "(none)",
                    record.state,
                    str(len(record.audit)),
                ],
            )
        if self._records:
            self.list.Select(0)
            self.list.Focus(0)
        self._show_audit()

    def _selected_record(self) -> ApprovalRecord | None:
        idx = self.list.GetFirstSelected()
        if idx < 0 or idx >= len(self._records):
            return None
        return self._records[idx]

    def _selected_draft_id(self) -> str:
        idx = self.draft.GetSelection()
        if idx < 0 or idx >= len(self._drafts):
            return ""
        return self._drafts[idx].draft_id

    def _current_role(self) -> str:
        return approvals_svc.ROLES[self.role.GetSelection()]

    def _show_audit(self) -> None:
        record = self._selected_record()
        if record is None:
            self.audit.SetValue("No record selected.")
            return
        lines = [f"State: {record.state}"]
        for entry in record.audit:
            lines.append(
                f"{_fmt_ms_utc(entry.at_ms)} UTC -- {entry.actor} ({entry.role}) "
                f"{entry.action}: {entry.from_state} to {entry.to_state}"
                + (f" -- {entry.note}" if entry.note else "")
            )
        if not record.audit:
            lines.append("No audit steps yet.")
        self.audit.SetValue("\n".join(lines))

    # -- actions -------------------------------------------------------------

    def _record_for_selected_draft(self) -> ApprovalRecord:
        draft_id = self._selected_draft_id()
        for record in self._records:
            if record.draft_id == draft_id and draft_id:
                return record
        return ApprovalRecord(draft_id=draft_id)

    def _guard(self, action: str) -> bool:
        role = self._current_role()
        if not approvals_svc.can_perform(role, action):
            wx.MessageBox(
                f"Role {role} may not {action}.",
                "Approvals",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return False
        return True

    def _apply(self, record: ApprovalRecord, mover) -> None:
        role = self._current_role()
        try:
            mover(record, actor=self._store.path.stem or "me", role=role)
        except ApprovalError as exc:
            wx.MessageBox(str(exc), "Approvals", wx.OK | wx.ICON_INFORMATION, self)
            return
        approvals_svc.save(self._store, record)
        self._reload_records()

    def _on_request(self) -> None:
        if not self._guard("submit"):
            return
        record = self._record_for_selected_draft()
        role = self._current_role()
        # Move an untouched idea to draft first so it can be submitted for review.
        if record.state == "idea":
            try:
                approvals_svc.transition(
                    record, "draft", actor=self._store.path.stem or "me", role=role
                )
            except ApprovalError as exc:
                wx.MessageBox(str(exc), "Approvals", wx.OK | wx.ICON_INFORMATION, self)
                return
        self._apply(record, approvals_svc.request_approval)

    def _on_approve(self) -> None:
        if not self._guard("approve"):
            return
        record = self._selected_record()
        if record is None:
            wx.MessageBox(
                "Select a record to approve.",
                "Approvals",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        self._apply(record, approvals_svc.approve)

    def _on_changes(self) -> None:
        if not self._guard("request_changes"):
            return
        record = self._selected_record()
        if record is None:
            wx.MessageBox(
                "Select a record to send back.",
                "Approvals",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        self._apply(record, approvals_svc.request_changes)


# -- shared helpers -----------------------------------------------------------


def _fmt_ms_utc(ms: int | None) -> str:
    """Format epoch milliseconds as a plain UTC ``YYYY-MM-DD HH:MM`` string."""
    if not ms:
        return "unscheduled"
    from datetime import UTC, datetime

    dt = datetime.fromtimestamp(ms / 1000, tz=UTC)
    return dt.strftime("%Y-%m-%d %H:%M")
