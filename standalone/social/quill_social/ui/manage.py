"""Accessible management dialogs for safety, notifications, plugins, and outbox.

Five keyboard-complete ``wx.Dialog`` surfaces that expose services already built
and tested elsewhere, so the desktop shell can manage its long-lived settings
without a mouse:

- :class:`SafetyCenterDialog` and :class:`FilterEditorDialog` -- the Unified
  Safety Center: local filters, a live filter preview, mutes and blocks
  (PRD 27).
- :class:`NotificationPoliciesDialog` -- per-category delivery policies and
  quiet hours (PRD 25).
- :class:`PluginManagerDialog` -- enable/disable plugins, safe mode, declared
  permissions, and degraded state (PRD 34).
- :class:`OutboxDialog` -- the offline outbox and its circuit-breaker state
  (PRD 32).

Every control carries a visible ``wx.StaticText`` label and an explicit
``SetName`` so a screen reader always has an accessible name, lists are
report-mode with named columns, and no action requires the mouse. The dialogs
are thin: all persistence and logic live in the pure services under
``quill_social.services``.
"""

from __future__ import annotations

import wx

from quill_social.model import now_ms
from quill_social.services import moderation as moderation_svc
from quill_social.services import notifications as notif_svc
from quill_social.services.moderation import Filter, MuteBlock
from quill_social.services.notifications import CATEGORIES, NotificationPolicy
from quill_social.services.outbox import CircuitBreaker, Outbox
from quill_social.services.plugins import PluginManifest, PluginRegistry

# The management UI persists plugin manifests (identity + permissions) under its
# own document kind; the registry itself only persists per-plugin state (PRD 34).
PLUGIN_MANIFEST_KIND = "plugin_manifest"

# Quiet-hours windows are per account and separate from a NotificationPolicy,
# which only records whether a category is suppressed during them (PRD 25.2).
QUIET_HOURS_KIND = "notification_quiet_hours"


# -- small accessibility helpers ----------------------------------------------


def _label(parent: wx.Window, sizer: wx.Sizer, text: str) -> None:
    """Add a visible field label to ``sizer`` (PRD 6.5, names are never implied)."""
    sizer.Add(wx.StaticText(parent, label=text), 0, wx.LEFT | wx.TOP, 6)


def _named(ctrl: wx.Window, name: str) -> wx.Window:
    """Give ``ctrl`` an explicit accessible name and return it."""
    ctrl.SetName(name)
    return ctrl


def _report_list(
    parent: wx.Window, name: str, columns: list[tuple[str, int]]
) -> wx.ListCtrl:
    """A single-selection report list with named columns for a screen reader."""
    lc = wx.ListCtrl(parent, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    lc.SetName(name)
    for i, (title, width) in enumerate(columns):
        lc.InsertColumn(i, title, width=width)
    return lc


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _parse_hhmm(text: str) -> int | None:
    """Parse ``HH:MM`` into a minute-of-day (0-1439); return None if invalid/empty."""
    text = text.strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) != 2:
        return None
    try:
        hours, minutes = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        return None
    return hours * 60 + minutes


def _fmt_hhmm(minutes: int | None) -> str:
    if minutes is None:
        return ""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# -- plugin manifest persistence (PRD 34) -------------------------------------


def save_plugin_manifest(store, manifest: PluginManifest) -> PluginManifest:
    """Persist a plugin manifest so the manager can list it after a restart."""
    store.put_document(PLUGIN_MANIFEST_KIND, manifest.id, manifest.to_dict())
    return manifest


def load_plugin_manifests(store) -> list[PluginManifest]:
    return [
        PluginManifest.from_dict(d) for d in store.list_documents(PLUGIN_MANIFEST_KIND)
    ]


# -- quiet-hours persistence (PRD 25.2) ---------------------------------------


def save_quiet_hours(store, account_id: str, start: int | None, end: int | None) -> None:
    store.put_document(
        QUIET_HOURS_KIND, account_id or "global", {"start": start, "end": end}
    )


def load_quiet_hours(store, account_id: str) -> tuple[int | None, int | None]:
    doc = store.get_document(QUIET_HOURS_KIND, account_id or "global") or {}
    return doc.get("start"), doc.get("end")


# -- filter editor (PRD 27.2) -------------------------------------------------

# The named criteria fields a filter can carry, paired with their control names.
_CRITERIA_FIELDS = (
    ("text", "Text contains"),
    ("regex", "Regular expression"),
    ("author", "Author handle"),
    ("network", "Network"),
    ("post_type", "Post type (post/reply/quote/repost)"),
    ("language", "Language code"),
    ("moderation_label", "Moderation label"),
)


class FilterEditorDialog(wx.Dialog):
    """Create or edit one local content filter (PRD 27.2).

    Exposes ``result_filter`` (a :class:`Filter`) once the user accepts; when
    editing, the original ``filter_id`` and creation time are preserved so the
    saved record updates in place rather than forking.
    """

    def __init__(self, parent: wx.Window, filter: Filter | None = None) -> None:
        super().__init__(
            parent,
            title="Edit Filter" if filter else "New Filter",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._source = filter
        self.result_filter: Filter | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)

        _label(self, sizer, "Filter name:")
        self.name = _named(wx.TextCtrl(self), "Filter name")
        if filter:
            self.name.SetValue(filter.name)
        sizer.Add(self.name, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        _label(self, sizer, "Match criteria (leave a field blank to ignore it):")
        self._criteria: dict[str, wx.TextCtrl] = {}
        criteria = filter.criteria if filter else {}
        for key, label_text in _CRITERIA_FIELDS:
            _label(self, sizer, label_text + ":")
            ctrl = _named(wx.TextCtrl(self), label_text)
            existing = criteria.get(key)
            if existing is not None:
                ctrl.SetValue(str(existing))
            sizer.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
            self._criteria[key] = ctrl

        _label(self, sizer, "Action:")
        self.action = _named(
            wx.Choice(self, choices=list(moderation_svc.ACTIONS)), "Action"
        )
        self.action.SetStringSelection(filter.action if filter else "hide")
        if self.action.GetSelection() == wx.NOT_FOUND:
            self.action.SetSelection(0)
        sizer.Add(self.action, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self.enabled = _named(wx.CheckBox(self, label="Filter enabled"), "Filter enabled")
        self.enabled.SetValue(filter.enabled if filter else True)
        sizer.Add(self.enabled, 0, wx.ALL, 6)

        sizer.Add(
            self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, 8
        )
        self.SetSizerAndFit(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.name.SetFocus()

    def build_filter(self) -> Filter:
        """Assemble a :class:`Filter` from the current field values."""
        criteria: dict[str, str] = {}
        for key, ctrl in self._criteria.items():
            value = ctrl.GetValue().strip()
            if value:
                criteria[key] = value
        base = self._source
        return Filter(
            filter_id=base.filter_id if base else Filter().filter_id,
            name=self.name.GetValue().strip(),
            criteria=criteria,
            action=self.action.GetStringSelection() or "hide",
            enabled=self.enabled.GetValue(),
            created=base.created if base else now_ms(),
        )

    def _on_ok(self, _event: wx.CommandEvent) -> None:
        self.result_filter = self.build_filter()
        self.EndModal(wx.ID_OK)


# -- safety center (PRD 27.1) -------------------------------------------------

_MUTEBLOCK_KINDS = ("mute", "block", "domain_block")
_MUTEBLOCK_SCOPES = ("all", "timeline", "notifications", "conversation")


class SafetyCenterDialog(wx.Dialog):
    """The Unified Safety Center: filters, live preview, mutes, and blocks (PRD 27.1)."""

    def __init__(self, parent: wx.Window, store) -> None:
        super().__init__(
            parent,
            title="Safety Center",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.store = store
        self._filters: list[Filter] = []
        self._muteblocks: list[MuteBlock] = []

        sizer = wx.BoxSizer(wx.VERTICAL)

        _label(self, sizer, "Overview:")
        self.summary = _named(
            wx.StaticText(self, label=""), "Safety center overview"
        )
        sizer.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        _label(self, sizer, "Local filters:")
        self.filter_list = _report_list(
            self,
            "Filters",
            [("Name", 160), ("Criteria", 220), ("Action", 110), ("Enabled", 70)],
        )
        sizer.Add(self.filter_list, 1, wx.EXPAND | wx.ALL, 6)

        frow = wx.BoxSizer(wx.HORIZONTAL)
        self.add_btn = _named(wx.Button(self, label="Add filter"), "Add filter")
        self.edit_btn = _named(wx.Button(self, label="Edit filter"), "Edit filter")
        self.del_btn = _named(wx.Button(self, label="Delete filter"), "Delete filter")
        for btn in (self.add_btn, self.edit_btn, self.del_btn):
            frow.Add(btn, 0, wx.RIGHT, 6)
        sizer.Add(frow, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        _label(self, sizer, "Preview against cached posts:")
        self.preview = _named(wx.StaticText(self, label=""), "Filter preview")
        sizer.Add(self.preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        _label(self, sizer, "Mutes and blocks:")
        self.mb_list = _report_list(
            self,
            "Mutes and blocks",
            [("Target", 200), ("Kind", 110), ("Scope", 120)],
        )
        sizer.Add(self.mb_list, 1, wx.EXPAND | wx.ALL, 6)

        mrow = wx.BoxSizer(wx.HORIZONTAL)
        mrow.Add(wx.StaticText(self, label="Target:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.mb_target = _named(wx.TextCtrl(self), "Mute or block target")
        mrow.Add(self.mb_target, 1, wx.RIGHT, 6)
        mrow.Add(wx.StaticText(self, label="Kind:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.mb_kind = _named(
            wx.Choice(self, choices=list(_MUTEBLOCK_KINDS)), "Mute or block kind"
        )
        self.mb_kind.SetSelection(0)
        mrow.Add(self.mb_kind, 0, wx.RIGHT, 6)
        mrow.Add(wx.StaticText(self, label="Scope:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.mb_scope = _named(
            wx.Choice(self, choices=list(_MUTEBLOCK_SCOPES)), "Mute or block scope"
        )
        self.mb_scope.SetSelection(0)
        mrow.Add(self.mb_scope, 0, wx.RIGHT, 6)
        self.mb_add = _named(wx.Button(self, label="Add"), "Add mute or block")
        self.mb_remove = _named(wx.Button(self, label="Remove"), "Remove mute or block")
        mrow.Add(self.mb_add, 0, wx.RIGHT, 6)
        mrow.Add(self.mb_remove, 0)
        sizer.Add(mrow, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        sizer.Add(self.CreateButtonSizer(wx.CLOSE), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetSize((680, 720))

        self.add_btn.Bind(wx.EVT_BUTTON, self._on_add_filter)
        self.edit_btn.Bind(wx.EVT_BUTTON, self._on_edit_filter)
        self.del_btn.Bind(wx.EVT_BUTTON, self._on_delete_filter)
        self.filter_list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self._update_preview())
        self.filter_list.Bind(wx.EVT_LIST_ITEM_FOCUSED, lambda _e: self._update_preview())
        self.mb_add.Bind(wx.EVT_BUTTON, self._on_add_muteblock)
        self.mb_remove.Bind(wx.EVT_BUTTON, self._on_remove_muteblock)
        self.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)

        self.reload()

    # -- data -----------------------------------------------------------------

    def reload(self) -> None:
        self._filters = moderation_svc.load_filters(self.store)
        self._muteblocks = moderation_svc.load_muteblocks(self.store)
        self._render_filters()
        self._render_muteblocks()
        self._update_summary()
        self._update_preview()

    def _render_filters(self) -> None:
        self.filter_list.DeleteAllItems()
        for i, flt in enumerate(self._filters):
            crit = ", ".join(f"{k}={v}" for k, v in flt.criteria.items()) or "(none)"
            self.filter_list.InsertItem(i, flt.name or "(unnamed)")
            self.filter_list.SetItem(i, 1, crit)
            self.filter_list.SetItem(i, 2, flt.action)
            self.filter_list.SetItem(i, 3, _yes_no(flt.enabled))

    def _render_muteblocks(self) -> None:
        self.mb_list.DeleteAllItems()
        for i, mb in enumerate(self._muteblocks):
            self.mb_list.InsertItem(i, mb.target or "(none)")
            self.mb_list.SetItem(i, 1, mb.kind)
            self.mb_list.SetItem(i, 2, mb.scope)

    def _update_summary(self) -> None:
        summary = moderation_svc.safety_center_summary(
            filters=self._filters, muteblocks=self._muteblocks
        )
        self.summary.SetLabel(
            f"Filters: {summary['filters']}   Muted: {summary['muted']}   "
            f"Blocked: {summary['blocked']}   Blocked domains: "
            f"{summary['blocked_domains']}"
        )

    def _selected_filter(self) -> Filter | None:
        idx = self.filter_list.GetFirstSelected()
        if 0 <= idx < len(self._filters):
            return self._filters[idx]
        return None

    def preview_counts(self, flt: Filter) -> tuple[int, int, int]:
        """Return (hidden, warned, total) if ``flt`` ran over cached posts (PRD 27.2).

        The filter is previewed as if enabled so the effect is visible even while
        a user is still deciding whether to switch it on.
        """
        items = self.store.list_items()
        probe = Filter(
            filter_id=flt.filter_id,
            name=flt.name,
            criteria=dict(flt.criteria),
            action=flt.action,
            enabled=True,
        )
        outcomes = moderation_svc.apply_filters(items, [probe])
        hidden = sum(1 for o in outcomes if o.hidden)
        warned = sum(1 for o in outcomes if o.warned)
        return hidden, warned, len(items)

    def _update_preview(self) -> None:
        flt = self._selected_filter()
        if flt is None:
            self.preview.SetLabel("Select a filter to preview its effect.")
            return
        hidden, warned, total = self.preview_counts(flt)
        self.preview.SetLabel(
            f"'{flt.name or 'unnamed'}' would hide {hidden} and warn/collapse "
            f"{warned} of {total} cached posts."
        )

    # -- filter events --------------------------------------------------------

    def _on_add_filter(self, _event: wx.CommandEvent) -> None:
        dlg = FilterEditorDialog(self)
        if dlg.ShowModal() == wx.ID_OK and dlg.result_filter:
            moderation_svc.save_filter(self.store, dlg.result_filter)
            self.reload()
        dlg.Destroy()

    def _on_edit_filter(self, _event: wx.CommandEvent) -> None:
        flt = self._selected_filter()
        if flt is None:
            return
        dlg = FilterEditorDialog(self, filter=flt)
        if dlg.ShowModal() == wx.ID_OK and dlg.result_filter:
            moderation_svc.save_filter(self.store, dlg.result_filter)
            self.reload()
        dlg.Destroy()

    def _on_delete_filter(self, _event: wx.CommandEvent) -> None:
        flt = self._selected_filter()
        if flt is None:
            return
        moderation_svc.delete_filter(self.store, flt.filter_id)
        self.reload()

    # -- mute/block events ----------------------------------------------------

    def _on_add_muteblock(self, _event: wx.CommandEvent) -> None:
        target = self.mb_target.GetValue().strip()
        if not target:
            return
        mb = MuteBlock(
            target=target,
            kind=self.mb_kind.GetStringSelection() or "mute",
            scope=self.mb_scope.GetStringSelection() or "all",
        )
        moderation_svc.save_muteblock(self.store, mb)
        self.mb_target.SetValue("")
        self.reload()

    def _on_remove_muteblock(self, _event: wx.CommandEvent) -> None:
        idx = self.mb_list.GetFirstSelected()
        if 0 <= idx < len(self._muteblocks):
            moderation_svc.delete_muteblock(self.store, self._muteblocks[idx].muteblock_id)
            self.reload()


# -- notification policies (PRD 25) -------------------------------------------

# (attribute, label) for each boolean channel a policy exposes.
_POLICY_FLAGS = (
    ("speak", "Speak"),
    ("braille", "Braille"),
    ("sound", "Sound"),
    ("desktop", "Desktop notification"),
    ("silent", "Add silently"),
    ("digest", "Include in digest"),
    ("suppress_during_quiet_hours", "Suppress during quiet hours"),
    ("group_duplicates", "Group duplicates"),
)


class NotificationPoliciesDialog(wx.Dialog):
    """Per-category notification delivery policies and quiet hours (PRD 25.2)."""

    def __init__(self, parent: wx.Window, store, account_id: str = "") -> None:
        super().__init__(
            parent,
            title="Notification Policies",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.store = store
        if not account_id:
            accounts = store.list_accounts() if hasattr(store, "list_accounts") else []
            default = next((a for a in accounts if a.is_default), None)
            account_id = (default or accounts[0]).account_id if accounts else ""
        self.account_id = account_id

        sizer = wx.BoxSizer(wx.VERTICAL)

        _label(self, sizer, "Category:")
        self.category = _named(
            wx.Choice(self, choices=list(CATEGORIES)), "Notification category"
        )
        self.category.SetSelection(0)
        sizer.Add(self.category, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self._flags: dict[str, wx.CheckBox] = {}
        for attr, label_text in _POLICY_FLAGS:
            box = _named(wx.CheckBox(self, label=label_text), label_text)
            sizer.Add(box, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
            self._flags[attr] = box

        _label(self, sizer, "Only from these handles (comma separated):")
        self.only_from = _named(wx.TextCtrl(self), "Only from handles")
        sizer.Add(self.only_from, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        qrow = wx.BoxSizer(wx.HORIZONTAL)
        qrow.Add(
            wx.StaticText(self, label="Quiet hours start (HH:MM):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self.quiet_start = _named(wx.TextCtrl(self), "Quiet hours start")
        qrow.Add(self.quiet_start, 0, wx.RIGHT, 12)
        qrow.Add(
            wx.StaticText(self, label="Quiet hours end (HH:MM):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self.quiet_end = _named(wx.TextCtrl(self), "Quiet hours end")
        qrow.Add(self.quiet_end, 0)
        sizer.Add(qrow, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        brow = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = _named(wx.Button(self, label="Save category"), "Save category")
        brow.Add(self.save_btn, 0, wx.RIGHT, 6)
        sizer.Add(brow, 0, wx.ALL, 6)
        sizer.Add(self.CreateButtonSizer(wx.CLOSE), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(sizer)

        self.category.Bind(wx.EVT_CHOICE, lambda _e: self._load_category())
        self.save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        self.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)

        start, end = load_quiet_hours(self.store, self.account_id)
        self.quiet_start.SetValue(_fmt_hhmm(start))
        self.quiet_end.SetValue(_fmt_hhmm(end))
        self._load_category()

    def current_category(self) -> str:
        return self.category.GetStringSelection() or CATEGORIES[0]

    def _load_category(self) -> None:
        category = self.current_category()
        policy = notif_svc.get_policy(self.store, self.account_id, category)
        if policy is None:
            policy = NotificationPolicy(account_id=self.account_id, category=category)
        for attr, box in self._flags.items():
            box.SetValue(bool(getattr(policy, attr)))
        self.only_from.SetValue(", ".join(policy.only_from))

    def build_policy(self) -> NotificationPolicy:
        """Assemble the :class:`NotificationPolicy` for the current category."""
        handles = [h.strip() for h in self.only_from.GetValue().split(",") if h.strip()]
        policy = NotificationPolicy(
            account_id=self.account_id, category=self.current_category()
        )
        for attr, box in self._flags.items():
            setattr(policy, attr, box.GetValue())
        policy.only_from = handles
        return policy

    def _on_save(self, _event: wx.CommandEvent) -> None:
        notif_svc.save_policy(self.store, self.build_policy())
        save_quiet_hours(
            self.store,
            self.account_id,
            _parse_hhmm(self.quiet_start.GetValue()),
            _parse_hhmm(self.quiet_end.GetValue()),
        )


# -- plugin manager (PRD 34) --------------------------------------------------


class PluginManagerDialog(wx.Dialog):
    """Enable/disable plugins, safe mode, permissions, and degraded state (PRD 34)."""

    def __init__(self, parent: wx.Window, store) -> None:
        super().__init__(
            parent,
            title="Plugin Manager",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.store = store
        self.registry = PluginRegistry(store)
        self._manifests: list[PluginManifest] = []

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.safe_mode = _named(
            wx.CheckBox(self, label="Safe mode (disable all third-party plugins)"),
            "Safe mode",
        )
        sizer.Add(self.safe_mode, 0, wx.ALL, 6)

        _label(self, sizer, "Installed plugins:")
        self.plugin_list = _report_list(
            self,
            "Plugins",
            [
                ("Name", 150),
                ("Kind", 120),
                ("Enabled", 70),
                ("Degraded", 70),
                ("Permissions", 200),
            ],
        )
        sizer.Add(self.plugin_list, 1, wx.EXPAND | wx.ALL, 6)

        brow = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_btn = _named(wx.Button(self, label="Enable"), "Enable plugin")
        self.disable_btn = _named(wx.Button(self, label="Disable"), "Disable plugin")
        brow.Add(self.enable_btn, 0, wx.RIGHT, 6)
        brow.Add(self.disable_btn, 0)
        sizer.Add(brow, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        sizer.Add(self.CreateButtonSizer(wx.CLOSE), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetSize((680, 480))

        self.safe_mode.Bind(wx.EVT_CHECKBOX, self._on_safe_mode)
        self.enable_btn.Bind(wx.EVT_BUTTON, lambda _e: self._set_enabled(True))
        self.disable_btn.Bind(wx.EVT_BUTTON, lambda _e: self._set_enabled(False))
        self.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)

        self.reload()

    def reload(self) -> None:
        self._manifests = load_plugin_manifests(self.store)
        for manifest in self._manifests:
            self.registry.load(manifest)
        self._render()

    def _render(self) -> None:
        self.plugin_list.DeleteAllItems()
        for i, manifest in enumerate(self._manifests):
            perms = ", ".join(manifest.declared_permissions) or "(none)"
            self.plugin_list.InsertItem(i, manifest.name or manifest.id or "(plugin)")
            self.plugin_list.SetItem(i, 1, manifest.kind)
            self.plugin_list.SetItem(i, 2, _yes_no(self.registry.is_enabled(manifest)))
            self.plugin_list.SetItem(i, 3, _yes_no(self.registry.is_degraded(manifest)))
            self.plugin_list.SetItem(i, 4, perms)

    def _selected(self) -> PluginManifest | None:
        idx = self.plugin_list.GetFirstSelected()
        if 0 <= idx < len(self._manifests):
            return self._manifests[idx]
        return None

    def _on_safe_mode(self, _event: wx.CommandEvent) -> None:
        self.registry.safe_mode = self.safe_mode.GetValue()
        self._render()

    def _set_enabled(self, enabled: bool) -> None:
        manifest = self._selected()
        if manifest is None:
            return
        if enabled:
            self.registry.enable(manifest)
        else:
            self.registry.disable(manifest)
        self._render()


# -- outbox (PRD 32) ----------------------------------------------------------


class OutboxDialog(wx.Dialog):
    """The offline outbox and its circuit-breaker state (PRD 32.2, 32.3)."""

    def __init__(
        self, parent: wx.Window, store, breaker: CircuitBreaker | None = None
    ) -> None:
        super().__init__(
            parent,
            title="Outbox",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.store = store
        self.outbox = Outbox(store)
        self.breaker = breaker or CircuitBreaker(service="outbox")
        self._items = []

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.breaker_text = _named(
            wx.StaticText(self, label=""), "Circuit breaker state"
        )
        sizer.Add(self.breaker_text, 0, wx.EXPAND | wx.ALL, 6)

        _label(self, sizer, "Queued posts:")
        self.item_list = _report_list(
            self,
            "Outbox items",
            [
                ("Account", 140),
                ("Network", 100),
                ("Created", 120),
                ("Send mode", 100),
                ("Validation", 100),
            ],
        )
        sizer.Add(self.item_list, 1, wx.EXPAND | wx.ALL, 6)

        brow = wx.BoxSizer(wx.HORIZONTAL)
        self.remove_btn = _named(wx.Button(self, label="Remove"), "Remove outbox item")
        brow.Add(self.remove_btn, 0)
        sizer.Add(brow, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        sizer.Add(self.CreateButtonSizer(wx.CLOSE), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetSize((640, 440))

        self.remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        self.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CLOSE), id=wx.ID_CLOSE)

        self.reload()

    def reload(self) -> None:
        self._items = self.outbox.list()
        self.breaker_text.SetLabel(
            f"Circuit breaker '{self.breaker.service or 'outbox'}': "
            f"{self.breaker.state} ({self.breaker.failures} recent failure(s))."
        )
        self.item_list.DeleteAllItems()
        for i, item in enumerate(self._items):
            self.item_list.InsertItem(i, item.account_id or "(none)")
            self.item_list.SetItem(i, 1, item.network)
            self.item_list.SetItem(i, 2, _fmt_created(item.created))
            self.item_list.SetItem(i, 3, item.send_mode)
            self.item_list.SetItem(i, 4, item.validation_status)

    def _on_remove(self, _event: wx.CommandEvent) -> None:
        idx = self.item_list.GetFirstSelected()
        if 0 <= idx < len(self._items):
            self.outbox.remove(self._items[idx].outbox_id)
            self.reload()


def _fmt_created(ms: int) -> str:
    if not ms:
        return "unknown"
    from datetime import UTC, datetime

    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M")
