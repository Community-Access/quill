"""Native list and detail surface for global and repository GitHub discovery."""

from __future__ import annotations

import threading
import webbrowser
from dataclasses import replace
from typing import TYPE_CHECKING

from quill.core.github.attention_queue import GitHubAttentionQueue
from quill.core.github.explore import ExploreRow, GitHubExploreClient, GitHubExploreError
from quill.core.github.explore_views import PERSON_VIEWS, QUERY_VIEWS, REPO_VIEWS, VIEW_NOTES, VIEWS
from quill.core.github.fetch_results import GitHubFetchResult
from quill.core.github.navigation_state import account_key_for_token
from quill.core.github.saved_items import GitHubSavedItems
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.github_explore_context_menu import GitHubExploreContextMenuMixin
from quill.ui.github_explore_labels import GitHubExploreLabelsMixin
from quill.ui.github_explore_notifications import GitHubExploreNotificationsMixin
from quill.ui.github_explore_queue import GitHubExploreQueueMixin
from quill.ui.github_explore_queue import queue_item_key as _queue_item_key
from quill.ui.github_explore_repo_actions import GitHubExploreRepoActionsMixin
from quill.ui.github_explore_search import GitHubExploreSearchMixin
from quill.ui.spoken_name import set_spoken_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider


class GitHubExploreDialog(
    GitHubExploreContextMenuMixin,
    GitHubExploreLabelsMixin,
    GitHubExploreRepoActionsMixin,
    GitHubExploreNotificationsMixin,
    GitHubExploreQueueMixin,
    GitHubExploreSearchMixin,
):
    """Shared QUILL/Lite account and repository views with selected-row actions."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        initial_repo: str = "",
        initial_view: str | None = None,
        initial_discussion: int | None = None,
        on_repo_select: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
        on_start_issue_worktree: Callable[[object, str, int, str, bool], None] | None = None,
        on_open_reference: Callable[[object], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._client = GitHubExploreClient(provider)
        self._saved = GitHubSavedItems.load(
            account_key=account_key_for_token(getattr(provider, "token", None))
        )
        self._initial_discussion = initial_discussion
        self._announce = announce_cb or (lambda _message: None)
        self._on_repo_select = on_repo_select
        self._on_start_issue_worktree = on_start_issue_worktree
        self._on_open_reference = on_open_reference
        self._rows: list[ExploreRow] = []
        self._attention_state: GitHubAttentionQueue | None = None
        self._selected_keys: dict[str, str] = {}
        self._include_snoozed = False
        self._load_token = 0
        self._write_token = 0
        self._write_in_flight = False
        self.dialog = wx.Dialog(
            parent, title="Explore GitHub", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 720, 500))
        self.dialog.SetSize(dip_size(self.dialog, 850, 640))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        controls = wx.BoxSizer(wx.HORIZONTAL)
        controls.Add(
            wx.StaticText(panel, label="&View:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
        )
        self._view = wx.Choice(panel, choices=[label for _, label in VIEWS])
        self._view.SetName("GitHub exploration view")
        keys = [key for key, _label in VIEWS]
        default_view = "attention" if provider.is_authenticated else "search"
        self._view.SetSelection(keys.index(initial_view if initial_view in keys else default_view))
        controls.Add(self._view, 1, wx.RIGHT, 10)
        controls.Add(
            wx.StaticText(panel, label="&Repository:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
        )
        self._repo = wx.TextCtrl(panel, value=initial_repo, style=wx.TE_PROCESS_ENTER)
        self._repo.SetName("Repository owner slash name for repository views")
        controls.Add(self._repo, 1)
        root.Add(controls, 0, wx.EXPAND | wx.ALL, 8)
        self._view_note = wx.StaticText(panel, label="")
        self._view_note.SetName("GitHub view description")
        self._view_note.Wrap(680)
        root.Add(self._view_note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self._view.Bind(wx.EVT_CHOICE, self._on_view_changed)
        self._on_view_changed(None)

        person_row = wx.BoxSizer(wx.HORIZONTAL)
        person_row.Add(
            wx.StaticText(panel, label="&Person:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
        )
        self._person = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._person.SetName("GitHub username for people views")
        person_row.Add(self._person, 1)
        root.Add(person_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        search = wx.BoxSizer(wx.HORIZONTAL)
        search.Add(
            wx.StaticText(panel, label="&Global search:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5
        )
        self._query = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._query.SetName("GitHub search query for the search views")
        self._query.SetHelpText(
            "What to search for. The view chooses what is searched: issues and pull "
            "requests, code, commits or repositories. GitHub qualifiers such as repo: work."
        )
        search.Add(self._query, 1, wx.RIGHT, 5)
        self._saved_btn = wx.Button(panel, label="Saved &Searches...")
        self._saved_btn.SetName("Choose or remove a saved global search")
        self._save_btn = wx.Button(panel, label="Save Search")
        self._save_btn.SetName("Save the current global search query locally")
        self._load_btn = wx.Button(panel, label="&Load")
        self._load_btn.SetName("Load selected GitHub exploration view")
        self._queue_options_btn = wx.Button(panel, label="Queue &Options...")
        self._queue_options_btn.SetName(
            "Choose attention queue repositories, categories, and saved filters"
        )
        for button in (self._saved_btn, self._save_btn, self._load_btn, self._queue_options_btn):
            search.Add(button, 0, wx.RIGHT, 5)
        root.Add(search, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(wx.StaticText(panel, label="Results"), 0, wx.LEFT, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName("GitHub exploration results; arrow to select, Tab to read details")
        set_spoken_name(self._list, "GitHub exploration results")
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._build_notification_controls(panel, root)
        root.Add(wx.StaticText(panel, label="Selected result"), 0, wx.LEFT | wx.TOP, 8)
        self._detail = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._detail.SetName("Selected GitHub result details")
        root.Add(self._detail, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="Choose a view and press Load.")
        self._status.SetName("GitHub exploration status")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        actions = wx.BoxSizer(wx.HORIZONTAL)
        self._open_btn = wx.Button(panel, label="Open on GitHub")
        self._open_btn.SetName("Open selected result in browser")
        self._use_btn = wx.Button(panel, label="Use Repository")
        self._use_btn.SetName("Load selected repository in the GitHub Items viewer")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close GitHub exploration")
        actions.Add(self._open_btn, 0, wx.RIGHT, 6)
        actions.Add(self._use_btn, 0, wx.RIGHT, 6)
        actions.AddStretchSpacer()
        actions.Add(close_btn)
        root.Add(actions, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._view.Bind(wx.EVT_CHOICE, self._load)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_explore_char_hook)
        self._load_btn.Bind(wx.EVT_BUTTON, self._load)
        self._repo.Bind(wx.EVT_TEXT_ENTER, self._load)
        self._person.Bind(wx.EVT_TEXT_ENTER, self._load)
        self._query.Bind(wx.EVT_TEXT_ENTER, self._load)
        self._save_btn.Bind(wx.EVT_BUTTON, self._save_search)
        self._saved_btn.Bind(wx.EVT_BUTTON, self._saved_searches_menu)
        self._queue_options_btn.Bind(wx.EVT_BUTTON, self._attention_options_menu)
        self._list.Bind(wx.EVT_LISTBOX, self._select)
        apply_listbox_activation(self._list, self._activate)
        self._list.Bind(wx.EVT_CONTEXT_MENU, self._context_menu)
        self._detail.Bind(wx.EVT_CONTEXT_MENU, self._context_menu)
        self._open_btn.Bind(wx.EVT_BUTTON, self._open)
        self._use_btn.Bind(wx.EVT_BUTTON, self._use_repo)
        self._open_btn.Enable(False)
        self._use_btn.Enable(False)
        self._queue_options_btn.Enable(False)
        self._update_notification_controls()

    def show(self) -> None:
        wx = self._wx
        if self._client._provider.is_authenticated:
            self._load(None)
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "Explore GitHub", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _view_key(self) -> str:
        return VIEWS[self._view.GetSelection()][0]

    def _on_view_changed(self, _event: object) -> None:
        self._view_note.SetLabel(VIEW_NOTES.get(self._view_key(), ""))
        self._update_notification_controls()

    def _load(self, _event: object) -> None:
        view = self._view_key()
        repo = self._repo.GetValue().strip()
        query = self._query.GetValue().strip()
        person = self._person.GetValue().strip()
        if view in REPO_VIEWS and (not repo or "/" not in repo):
            self._status.SetLabel("Enter a repository as owner/repo for this view.")
            self._repo.SetFocus()
            return
        if view in QUERY_VIEWS and not query:
            self._status.SetLabel("Enter a search query first.")
            self._query.SetFocus()
            return
        if view in PERSON_VIEWS and not person:
            self._status.SetLabel("Enter a GitHub username for this people view.")
            self._person.SetFocus()
            return
        self._queue_options_btn.Enable(view == "attention" and self._attention_state is not None)
        self._load_token += 1
        token = self._load_token
        selected_key = self._selected_keys.get(view, "")
        discussion_number = self._initial_discussion
        if view == "notifications" and self._notification_poll_blocks(token, selected_key):
            return
        include_read = (
            {"include_read": self._include_read_value()} if view == "notifications" else {}
        )
        self._status.SetLabel(f"Loading {dict(VIEWS)[view]}...")

        def worker() -> None:
            wx = self._wx
            try:
                queue_state = None
                repositories: tuple[str, ...] = ()
                categories: tuple[str, ...] = ()
                if view == "attention":
                    queue_state = GitHubAttentionQueue.load(self._client.account_login())
                    repositories = tuple(queue_state.repositories)
                    categories = tuple(queue_state.categories)
                if view == "discussions" and discussion_number is not None:
                    result = GitHubFetchResult((
                        self._client.fetch_discussion(repo, discussion_number),
                    ))
                else:
                    result = self._client.fetch_with_status(
                        view,
                        repo=repo,
                        query=query,
                        person=person,
                        repositories=repositories,
                        categories=categories,
                        **include_read,
                    )
            except GitHubExploreError as exc:
                wx.CallAfter(self._loaded, token, None, str(exc), None, view, selected_key)
                return
            wx.CallAfter(self._loaded, token, result, "", queue_state, view, selected_key)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: GitHub fetch.

    def _loaded(
        self,
        token: int,
        result: GitHubFetchResult[ExploreRow] | None,
        error: str,
        queue_state: GitHubAttentionQueue | None = None,
        view: str | None = None,
        selected_key: str = "",
    ) -> None:
        if token != self._load_token or not dialog_alive(self.dialog):
            return
        view = view or self._view_key()
        if view == "discussions" and self._initial_discussion is not None:
            self._initial_discussion = None
        if view == "attention":
            self._attention_state = queue_state
        self._rows = list(result.items) if result is not None else []
        changed_count = 0
        had_previous_visit = bool(queue_state and queue_state.last_visit_at)
        if view == "attention" and queue_state is not None and result is not None:
            visible: list[ExploreRow] = []
            for row in self._rows:
                changed = queue_state.changed_since_last_visit(row.updated_at)
                key = _queue_item_key(row)
                snoozed = queue_state.is_snoozed(key)
                if snoozed and not self._include_snoozed:
                    continue
                changed_count += int(changed)
                notes = []
                if snoozed:
                    notes.append(f"Snoozed locally until {queue_state.snoozed[key]}.")
                if changed:
                    notes.append("Changed since your last visit.")
                visible.append(
                    replace(row, detail=f"{' '.join(notes)}\n{row.detail}") if notes else row
                )
            self._rows = visible
            if result.complete:
                queue_state.mark_visited()
        if view == "chooser":
            saved: list[ExploreRow] = []
            for source, names in (
                ("Pinned", self._saved.pinned),
                ("Recent", self._saved.recent or []),
            ):
                for repo in names:
                    url = f"https://github.com/{repo}"
                    saved.append(
                        ExploreRow(
                            f"{source}: {repo}",
                            f"{source} repository: {repo}\n{url}",
                            url,
                            repo,
                            "repo",
                        )
                    )
            seen: set[str] = set()
            merged: list[ExploreRow] = []
            for row in saved + self._rows:
                if row.repo.casefold() not in seen:
                    seen.add(row.repo.casefold())
                    merged.append(row)
            self._rows = merged
        self._list.Set([row.label for row in self._rows])
        self._detail.SetValue("")
        self._open_btn.Enable(False)
        self._use_btn.Enable(False)
        queue_options = getattr(self, "_queue_options_btn", None)
        if queue_options is not None:
            queue_options.Enable(view == "attention" and queue_state is not None)
        if error:
            message = f"Could not load view: {error}"
        elif result is not None and not result.complete:
            message = f"{len(self._rows)} results loaded; this view is incomplete. {result.warning}"
        elif view == "notifications" and result is not None:
            message = self._notifications_loaded_message()
        else:
            message = self._note_if_unchanged(view, f"{len(self._rows)} results loaded.")
        if view == "attention" and not error:
            if queue_state is not None and had_previous_visit and result is not None:
                message += f" {changed_count} changed since your last visit."
            elif (
                queue_state is not None
                and not had_previous_visit
                and result is not None
                and result.complete
            ):
                message += " This is your first recorded visit."
            elif queue_state is not None and not had_previous_visit and result is not None:
                message += " No completed visit is recorded yet."
        self._status.SetLabel(message)
        self._announce(
            f"{len(self._rows)} results loaded with incomplete data. Check the status for details."
            if result is not None and not result.complete and not error
            else message
        )
        if self._rows:
            restore = next(
                (
                    index
                    for index, row in enumerate(self._rows)
                    if _queue_item_key(row) == selected_key
                ),
                0,
            )
            self._list.SetSelection(restore)
            self._select(None)
        self._update_notification_controls()

    def _selected(self) -> ExploreRow | None:
        index = self._list.GetSelection()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _select(self, _event: object) -> None:
        row = self._selected()
        if row:
            self._selected_keys[self._view_key()] = _queue_item_key(row)
        self._detail.SetValue(row.detail if row else "")
        self._open_btn.Enable(bool(row and row.url))
        self._use_btn.Enable(bool(row and row.repo))
        self._update_notification_controls()

    def _activate(self, _event: object) -> None:
        row = self._selected()
        if row and row.kind == "notification":
            self._activate_notification(row)
        elif row and row.repo and row.kind == "repo":
            self._use_repo(None)
        else:
            self._open(None)

    def _open(self, _event: object) -> None:
        row = self._selected()
        if row and row.url:
            self._announce(
                "Opened on GitHub." if webbrowser.open(row.url) else "Could not open the link."
            )

    def _use_repo(self, _event: object) -> None:
        row = self._selected()
        if row and row.repo and self._on_repo_select:
            self._on_repo_select(row.repo)
            self._announce(f"Selected repository {row.repo} in the workbench.")
            self.dialog.EndModal(self._wx.ID_OK)

    def _copy(self, value: str, what: str) -> None:
        wx = self._wx
        if not wx.TheClipboard.Open():
            self._announce("Could not open the clipboard.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(value))
        finally:
            wx.TheClipboard.Close()
        self._announce(f"Copied {what}." if copied else f"Could not copy {what}.")

    def _explore_person(self, login: str) -> None:
        self._person.SetValue(login)
        self._view.SetSelection(
            next(i for i, (key, _) in enumerate(VIEWS) if key == "person_activity")
        )
        self._load(None)

    def _mark_notification_read(self, notification_id: str) -> None:
        self._run_write(
            lambda: self._client.mark_notification_read(notification_id),
            "Notification marked as read.",
        )

    def _run_write(self, action: Callable[[], None], success: str) -> None:
        if self._write_in_flight:
            self._announce("Wait for the current GitHub action to finish before starting another.")
            return
        self._write_in_flight = True
        self._write_token += 1
        token = self._write_token
        self._status.SetLabel("Sending action to GitHub...")

        def worker() -> None:
            wx = self._wx
            try:
                action()
            except GitHubExploreError as exc:
                wx.CallAfter(self._write_done, token, f"Action failed: {exc}", False)
                return
            except Exception as exc:  # noqa: BLE001 - report unexpected provider failures
                wx.CallAfter(self._write_done, token, f"Action failed unexpectedly: {exc}", False)
                return
            wx.CallAfter(self._write_done, token, success, True)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: GitHub write.

    def _write_done(self, token: int, message: str, reload_view: bool) -> None:
        if token != self._write_token or not dialog_alive(self.dialog):
            return
        self._write_in_flight = False
        self._status.SetLabel(message)
        self._announce(message)
        if reload_view:
            self._load(None)

    def _change_repo(
        self, repo: str, *, watched: bool | None = None, starred: bool | None = None
    ) -> None:
        if watched is not None:
            verb = "Watch" if watched else "Unwatch"

            def action() -> None:
                self._client.set_watched(repo, watched)

        else:
            verb = "Star" if starred else "Unstar"

            def action() -> None:
                self._client.set_starred(repo, bool(starred))

        if self._confirm(f"{verb} {repo}?", f"{verb} Repository"):
            self._run_write(action, f"{verb} action completed for {repo}.")

    def _confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        with wx.MessageDialog(self.dialog, message, title, wx.YES_NO | wx.NO_DEFAULT) as dialog:
            return show_modal_dialog(dialog, title, announce=self._announce) == wx.ID_YES

    def _prompt(self, message: str, title: str, default: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.dialog, message, title, default) as dialog:
            if show_modal_dialog(dialog, title, announce=self._announce) != wx.ID_OK:
                return None
            return dialog.GetValue().strip()
