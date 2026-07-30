"""Accessible per-feed configuration dialog (plan xxx.md 1.5 "Per-feed config").

One keyboard-complete ``wx.Dialog`` that edits a single :class:`Subscription`:
its title, refresh cadence, retention, full-text and notify toggles, and its
per-feed keyword rules. The subscription document already persists every field
(``services.subscriptions``); this dialog is a thin, screen-reader-first editor
over it. Every control carries a visible label and an explicit ``SetName``, the
rules list is a reorderable ``ListBox`` driven by Add / Remove / Up / Down (no
checkboxes in a list, per the project's list-UI convention), and nothing needs
the mouse.
"""

from __future__ import annotations

import wx

from quill_social.services.feed_filters import FEED_ACTIONS
from quill_social.services.subscriptions import Subscription

# Refresh cadence presets, label -> seconds. 0 means manual-only.
_INTERVAL_PRESETS: list[tuple[str, int]] = [
    ("Every 5 minutes", 300),
    ("Every 15 minutes", 900),
    ("Every 30 minutes", 1800),
    ("Every hour", 3600),
    ("Every 6 hours", 21600),
    ("Manual only (no auto-refresh)", 0),
]


def _label(parent: wx.Window, sizer: wx.Sizer, text: str) -> None:
    sizer.Add(wx.StaticText(parent, label=text), 0, wx.LEFT | wx.TOP, 6)


def _named(ctrl: wx.Window, name: str) -> wx.Window:
    ctrl.SetName(name)
    return ctrl


def _rule_label(rule: dict) -> str:
    """A spoken, human-readable label for one keyword rule."""
    verb = {
        "hide": "Hide",
        "mark_read": "Mark read",
        "star": "Star",
    }.get(rule.get("action", ""), rule.get("action", ""))
    return f"{verb}: {rule.get('keyword', '')}"


def _interval_choices(current: int) -> list[tuple[str, int]]:
    """Preset intervals, guaranteeing the feed's current value is selectable."""
    presets = list(_INTERVAL_PRESETS)
    if current not in {secs for _label, secs in presets}:
        mins = max(1, round(current / 60))
        presets.insert(0, (f"Every {mins} minute(s) (current)", current))
    return presets


class FeedConfigDialog(wx.Dialog):
    """Edit one feed subscription's cadence, retention, toggles, and rules.

    On accept, ``result_subscription`` holds an updated :class:`Subscription`
    (the durable identity -- account id, URL, validators, timestamps -- is always
    preserved so the record updates in place).
    """

    def __init__(self, parent: wx.Window, sub: Subscription) -> None:
        super().__init__(
            parent,
            title=f"Feed settings: {sub.title or sub.feed_url}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._source = sub
        self.result_subscription: Subscription | None = None
        self._rules: list[dict] = [dict(r) for r in sub.filters]
        self._intervals = _interval_choices(sub.refresh_interval_s)

        sizer = wx.BoxSizer(wx.VERTICAL)

        _label(self, sizer, "Feed &title:")
        self.title = _named(wx.TextCtrl(self), "Feed title")
        self.title.SetValue(sub.title)
        sizer.Add(self.title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        _label(self, sizer, "&Refresh:")
        self.interval = _named(
            wx.Choice(self, choices=[lbl for lbl, _ in self._intervals]), "Refresh interval"
        )
        self.interval.SetSelection(
            next(
                (i for i, (_l, s) in enumerate(self._intervals) if s == sub.refresh_interval_s),
                0,
            )
        )
        sizer.Add(self.interval, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        _label(self, sizer, "&Keep articles for (days, 0 = keep forever):")
        self.retention = _named(
            wx.SpinCtrl(self, min=0, max=3650, initial=sub.retention_days), "Retention days"
        )
        sizer.Add(self.retention, 0, wx.LEFT | wx.RIGHT, 6)

        self.full_text = _named(
            wx.CheckBox(self, label="Fetch the &full article for truncated feeds"),
            "Fetch full article",
        )
        self.full_text.SetValue(sub.full_text)
        sizer.Add(self.full_text, 0, wx.ALL, 6)

        self.notify = _named(
            wx.CheckBox(self, label="A&nnounce new articles from this feed"),
            "Announce new articles",
        )
        self.notify.SetValue(sub.notify)
        sizer.Add(self.notify, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        # -- keyword rules ----------------------------------------------------
        _label(self, sizer, "Keyword rules (applied to new articles, top to bottom):")
        self.rule_list = _named(wx.ListBox(self, style=wx.LB_SINGLE), "Keyword rules")
        sizer.Add(self.rule_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        entry = wx.BoxSizer(wx.HORIZONTAL)
        entry.Add(
            wx.StaticText(self, label="&Word/phrase:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self.keyword = _named(wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER), "Keyword")
        entry.Add(self.keyword, 1, wx.RIGHT, 6)
        entry.Add(wx.StaticText(self, label="&Action:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.action = _named(wx.Choice(self, choices=list(FEED_ACTIONS)), "Rule action")
        self.action.SetSelection(0)
        entry.Add(self.action, 0, wx.RIGHT, 6)
        self.add_btn = _named(wx.Button(self, label="A&dd rule"), "Add rule")
        entry.Add(self.add_btn, 0)
        sizer.Add(entry, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)

        rrow = wx.BoxSizer(wx.HORIZONTAL)
        self.remove_btn = _named(wx.Button(self, label="Re&move rule"), "Remove rule")
        self.up_btn = _named(wx.Button(self, label="Move &up"), "Move rule up")
        self.down_btn = _named(wx.Button(self, label="Move dow&n"), "Move rule down")
        for b in (self.remove_btn, self.up_btn, self.down_btn):
            rrow.Add(b, 0, wx.RIGHT, 6)
        sizer.Add(rrow, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.TOP, 6)

        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizer(sizer)
        self.SetSize((560, 620))

        self.add_btn.Bind(wx.EVT_BUTTON, self._on_add_rule)
        self.keyword.Bind(wx.EVT_TEXT_ENTER, self._on_add_rule)
        self.remove_btn.Bind(wx.EVT_BUTTON, self._on_remove_rule)
        self.up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self.down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

        self._render_rules()
        self.title.SetFocus()

    # -- rules ----------------------------------------------------------------

    def _render_rules(self, select: int = -1) -> None:
        self.rule_list.Clear()
        for rule in self._rules:
            self.rule_list.Append(_rule_label(rule))
        if self._rules:
            idx = select if 0 <= select < len(self._rules) else 0
            self.rule_list.SetSelection(idx)

    def _announce(self, text: str) -> None:
        parent = self.GetParent()
        if parent is not None and hasattr(parent, "announcer"):
            parent.announcer.say(text, "normal", interrupt=True)

    def _on_add_rule(self, _event: wx.CommandEvent) -> None:
        keyword = self.keyword.GetValue().strip()
        if not keyword:
            self._announce("Enter a word or phrase for the rule.")
            self.keyword.SetFocus()
            return
        action = self.action.GetStringSelection() or FEED_ACTIONS[0]
        self._rules.append({"keyword": keyword, "action": action})
        self.keyword.SetValue("")
        self._render_rules(select=len(self._rules) - 1)
        self.keyword.SetFocus()
        self._announce(f"Added rule {_rule_label(self._rules[-1])}.")

    def _on_remove_rule(self, _event: wx.CommandEvent) -> None:
        idx = self.rule_list.GetSelection()
        if idx == wx.NOT_FOUND or not (0 <= idx < len(self._rules)):
            return
        removed = self._rules.pop(idx)
        self._render_rules(select=min(idx, len(self._rules) - 1))
        self._announce(f"Removed rule {_rule_label(removed)}.")

    def _move(self, delta: int) -> None:
        idx = self.rule_list.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        target = idx + delta
        if not (0 <= target < len(self._rules)):
            return
        self._rules[idx], self._rules[target] = self._rules[target], self._rules[idx]
        self._render_rules(select=target)

    # -- accept ---------------------------------------------------------------

    def build_subscription(self) -> Subscription:
        """Assemble the updated subscription from the current field values."""
        base = self._source
        interval = self._intervals[self.interval.GetSelection()][1]
        return Subscription(
            account_id=base.account_id,
            feed_url=base.feed_url,
            title=self.title.GetValue().strip() or base.title,
            site_url=base.site_url,
            folder_id=base.folder_id,
            tags=list(base.tags),
            refresh_interval_s=interval,
            retention_days=self.retention.GetValue(),
            notify=self.notify.GetValue(),
            full_text=self.full_text.GetValue(),
            filters=[dict(r) for r in self._rules],
            etag=base.etag,
            last_modified=base.last_modified,
            last_fetched=base.last_fetched,
            added=base.added,
        )

    def _on_ok(self, _event: wx.CommandEvent) -> None:
        self.result_subscription = self.build_subscription()
        self.EndModal(wx.ID_OK)


class SmartFolderDialog(wx.Dialog):
    """Create or edit a smart folder / saved search over cached articles.

    A smart folder is a saved predicate (``services.smartfolder``): the dialog
    edits its human-readable clauses and emits a plain rule dict plus a name. An
    empty rule is rejected so a saved search can never silently match the whole
    library. When editing, ``result_folder_id`` echoes the source id so the shell
    updates the record in place.
    """

    def __init__(
        self, parent: wx.Window, *, name: str = "", rule: dict | None = None, folder_id: str = ""
    ) -> None:
        super().__init__(
            parent,
            title="Edit Smart Folder" if folder_id else "New Smart Folder",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        rule = rule or {}
        self.result_name = ""
        self.result_rule: dict = {}
        self.result_folder_id = folder_id

        sizer = wx.BoxSizer(wx.VERTICAL)

        _label(self, sizer, "&Name:")
        self.name = _named(wx.TextCtrl(self), "Smart folder name")
        self.name.SetValue(name)
        sizer.Add(self.name, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        _label(self, sizer, "Contains &word/phrase (blank = any):")
        self.keyword = _named(wx.TextCtrl(self), "Keyword")
        self.keyword.SetValue(str(rule.get("keyword", "")))
        sizer.Add(self.keyword, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        _label(self, sizer, "&Author contains (blank = any):")
        self.author = _named(wx.TextCtrl(self), "Author contains")
        self.author.SetValue(str(rule.get("author", "")))
        sizer.Add(self.author, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self.unread = _named(wx.CheckBox(self, label="&Unread only"), "Unread only")
        self.unread.SetValue(rule.get("unread") is True)
        sizer.Add(self.unread, 0, wx.ALL, 6)

        self.has_media = _named(
            wx.CheckBox(self, label="Only items with &media"), "Only items with media"
        )
        self.has_media.SetValue(rule.get("has_media") is True)
        sizer.Add(self.has_media, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.bookmarked = _named(wx.CheckBox(self, label="&Bookmarked only"), "Bookmarked only")
        self.bookmarked.SetValue(rule.get("bookmarked") is True)
        sizer.Add(self.bookmarked, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        _label(self, sizer, "Minimum &engagement (replies+boosts+likes, 0 = any):")
        self.min_engagement = _named(
            wx.SpinCtrl(self, min=0, max=100000, initial=int(rule.get("min_engagement", 0) or 0)),
            "Minimum engagement",
        )
        sizer.Add(self.min_engagement, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.name.SetFocus()

    def build_rule(self) -> dict:
        """Assemble a smartfolder rule dict, omitting empty/unset clauses."""
        rule: dict = {}
        kw = self.keyword.GetValue().strip()
        if kw:
            rule["keyword"] = kw
        author = self.author.GetValue().strip()
        if author:
            rule["author"] = author
        if self.unread.GetValue():
            rule["unread"] = True
        if self.has_media.GetValue():
            rule["has_media"] = True
        if self.bookmarked.GetValue():
            rule["bookmarked"] = True
        eng = self.min_engagement.GetValue()
        if eng > 0:
            rule["min_engagement"] = eng
        return rule

    def _announce(self, text: str) -> None:
        parent = self.GetParent()
        if parent is not None and hasattr(parent, "announcer"):
            parent.announcer.say(text, "normal", interrupt=True)

    def _on_ok(self, _event: wx.CommandEvent) -> None:
        name = self.name.GetValue().strip()
        rule = self.build_rule()
        if not name:
            self._announce("Enter a name for the smart folder.")
            self.name.SetFocus()
            return
        if not rule:
            self._announce("Choose at least one condition, or the folder matches everything.")
            self.keyword.SetFocus()
            return
        self.result_name = name
        self.result_rule = rule
        self.EndModal(wx.ID_OK)
