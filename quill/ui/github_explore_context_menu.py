"""The Explore dialog's context menu (Shift+F10 or the Applications key).

Moved out of :mod:`quill.ui.github_explore_dialog` on 2026-11-07 (GATE-11). It
offers the actions that fit the selected row and the current view; each action
is a method on the dialog, so this module only decides what to list.
"""

from __future__ import annotations

from quill.core.github.explore_views import QUERY_VIEWS
from quill.ui.github_explore_queue import queue_item_key as _queue_item_key

__all__ = ["GitHubExploreContextMenuMixin"]


class GitHubExploreContextMenuMixin:
    """Build and show the row and view actions for the Explore list."""

    def _context_menu(self, event: object) -> None:
        wx = self._wx
        if event is not None and event.GetEventObject() is self._list:
            position = event.GetPosition()
            if position != wx.DefaultPosition:
                index = self._list.HitTest(self._list.ScreenToClient(position))
                if index != wx.NOT_FOUND:
                    self._list.SetSelection(index)
                    self._select(None)
        menu = wx.Menu()

        def add(label: str, action: object, enabled: bool = True) -> None:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Enable(item_id, enabled)
            menu.Bind(wx.EVT_MENU, lambda _event, callback=action: callback(), id=item_id)

        row = self._selected()
        if row:
            add("Open on GitHub", lambda: self._open(None), bool(row.url))
            add("Copy Link", lambda: self._copy(row.url, "link"), bool(row.url))
            add("Copy Details", lambda: self._copy(row.detail, "details"))
            add("Use Repository", lambda: self._use_repo(None), bool(row.repo))
            if row.kind == "repo" and self._client._provider.is_authenticated:
                add("Watch Repository", lambda: self._change_repo(row.repo, watched=True))
                add("Unwatch Repository", lambda: self._change_repo(row.repo, watched=False))
                add("Star Repository", lambda: self._change_repo(row.repo, starred=True))
                add("Unstar Repository", lambda: self._change_repo(row.repo, starred=False))
            if row.kind == "person":
                add("Explore Person's Activity", lambda: self._explore_person(row.key))
            if row.kind == "notification" and row.key:
                add("Mark Notification Read", lambda: self._mark_seen(row.key))
                add("Mark Done\tDelete", lambda: self._triage_notification(False))
                add("Unsubscribe from Thread", lambda: self._triage_notification(True))
        if self._view_key() == "notifications" and self._rows:
            add("Mark All Read...", self._mark_all_read)
            if (
                row.kind in {"issue", "pr"}
                and row.key.isdecimal()
                and self._on_start_issue_worktree is not None
            ):
                add(
                    "Start in Local Worktree...",
                    lambda item=row: self._on_start_issue_worktree(
                        self.dialog,
                        item.repo,
                        int(item.key),
                        item.title or item.label,
                        item.kind == "pr",
                    ),
                )
            if row.kind == "label" and self._client._provider.is_authenticated:
                add("Edit Label...", lambda: self._edit_label(row))
                add("Delete Label...", lambda: self._delete_label(row))
            if row.kind == "label":
                add("Find Issues with Label", lambda: self._find_label_issues(row))
            if self._view_key() == "attention" and self._attention_state is not None:
                key = _queue_item_key(row)
                if self._attention_state.is_snoozed(key):
                    add("Unsnooze Locally", lambda: self._unsnooze_attention_item(key))
                else:
                    add("Snooze for One Day", lambda: self._snooze_attention_item(key))
        if self._view_key() == "labels" and self._client._provider.is_authenticated:
            add("Create Label...", self._create_label)
        if self._view_key() in QUERY_VIEWS and self._query.GetValue().strip():
            query = self._query.GetValue().strip()
            add("Save Search", lambda: self._save_search(None))
            add("Remove Saved Search", lambda: self._remove_search(query))
        if self._view_key() == "attention" and self._attention_state is not None:
            add("Queue Options...", lambda: self._attention_options_menu(None))
        self._add_community_actions(add)
        self._add_wave4_actions(menu, add, row)
        add("Refresh", lambda: self._load(None))
        try:
            self._list.PopupMenu(menu)
        finally:
            menu.Destroy()
