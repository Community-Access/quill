"""Dialogs for File > Open Remote > GitHub (File-GH-1 through File-GH-4).

All surfaces use native wxPython controls. Dialogs collect input and return
plain data; side effects (token persistence, file download, tab creation) live
in ``GitHubRemoteMixin`` (``main_frame_github.py``).

Accessibility contract:
- Every interactive control has a ``SetName`` accessible name.
- Errors and progress messages are spoken via the status label (screen readers
  will announce them when focus moves; callers may also use ``_announce``).
- No custom-drawn controls.
- All navigation is keyboard-completable.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

if TYPE_CHECKING:
    from quill.core.github.github_provider import GitHubRemoteProvider
    from quill.core.github.models import BrowseResult, RemoteNode, RemoteRef, RemoteRepository

# Cap for the first-pass refs fetch in the browser dialog.  Anonymous GitHub
# has a 60-req/hour limit and a popular repo can have thousands of branches,
# so we show the default branch plus up to 99 more and offer a "Show all
# refs" affordance to opt into the full fetch (finding #34).
LIST_REFS_INITIAL_LIMIT = 100
LIST_REFS_FULL_LIMIT = 5_000

# ---------------------------------------------------------------------------
# Consent dialog (one-time, shown before any GitHub network access)
# ---------------------------------------------------------------------------

_CONSENT_TEXT = (
    "QUILL can connect to GitHub to browse repositories and open files you choose.\n\n"
    "No content is downloaded until you select a file. You can remove GitHub access "
    "later from File > Open Remote > Manage GitHub Accounts.\n\n"
    "Do you want to continue?"
)


class GitHubConsentDialog:
    """One-time network-access notice. Returns True if the user accepts."""

    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(parent, title="GitHub Access", style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)
        text = wx.StaticText(panel, label=_CONSENT_TEXT)
        text.Wrap(440)
        sizer.Add(text, flag=wx.ALL, border=12)
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Continue")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(wx.Button(panel, wx.ID_CANCEL, label="Cancel"))
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)
        self.dialog.SetSizerAndFit(wx.BoxSizer(wx.VERTICAL))
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()

    def show(self) -> bool:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            return show_modal_dialog(self.dialog, "GitHub Access") == wx.ID_OK
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Sign-in dialog (token entry or anonymous)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SignInResult:
    """Token or empty string for anonymous."""

    token: str  # "" means anonymous


class GitHubSignInDialog:
    """Collect a GitHub personal access token or allow anonymous access."""

    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(parent, title="Sign in to GitHub", style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label=(
                "Enter a GitHub personal access token to browse private repositories,\n"
                "or continue anonymously to browse public repositories only."
            ),
        )
        intro.Wrap(440)
        sizer.Add(intro, flag=wx.ALL, border=12)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)
        token_label = wx.StaticText(panel, label="Personal access token")
        self._token_ctrl = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._token_ctrl.SetName("Personal access token")
        grid.Add(token_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._token_ctrl, 1, wx.EXPAND)
        sizer.Add(grid, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        help_text = wx.StaticText(
            panel,
            label=(
                "Create a token at github.com > Settings > Developer settings >\n"
                "Personal access tokens. Select 'repo' scope for private repos."
            ),
        )
        help_text.Wrap(440)
        sizer.Add(help_text, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        self._connect_btn = wx.Button(panel, wx.ID_OK, label="Connect")
        self._connect_btn.SetDefault()
        btn_sizer.AddButton(self._connect_btn)
        anon_btn = wx.Button(panel, wx.ID_APPLY, label="Continue Anonymously")
        btn_sizer.AddButton(anon_btn)
        btn_sizer.AddButton(wx.Button(panel, wx.ID_CANCEL, label="Cancel"))
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        anon_btn.Bind(wx.EVT_BUTTON, self._on_anonymous)

    def _on_anonymous(self, _event: object) -> None:
        self.dialog.EndModal(self._wx.ID_APPLY)

    def show(self) -> SignInResult | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            result = show_modal_dialog(self.dialog, "Sign in to GitHub")
            if result == wx.ID_CANCEL:
                return None
            if result == wx.ID_APPLY:
                return SignInResult(token="")
            token = self._token_ctrl.GetValue().strip()
            if not token:
                return SignInResult(token="")
            return SignInResult(token=token)
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Manage accounts dialog
# ---------------------------------------------------------------------------


class GitHubManageAccountsDialog:
    """Show stored GitHub accounts; allow sign-out."""

    def __init__(self, parent: object, *, login: str | None, has_token: bool) -> None:
        import wx

        self._wx = wx
        self._removed = False
        self.dialog = wx.Dialog(
            parent, title="Manage GitHub Accounts", style=wx.DEFAULT_DIALOG_STYLE
        )
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        if has_token and login:
            status_text = f"Signed in as: {login}"
        elif has_token:
            status_text = "Token stored (could not verify identity)"
        else:
            status_text = "No GitHub account connected (anonymous access)"

        status = wx.StaticText(panel, label=status_text)
        status.SetName("GitHub account status")
        sizer.Add(status, flag=wx.ALL, border=12)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        if has_token:
            sign_out_btn = wx.Button(panel, wx.ID_REMOVE, label="Sign Out and Clear Token")
            sign_out_btn.SetName("Sign Out and Clear Token")
            btn_sizer.Add(sign_out_btn, flag=wx.RIGHT, border=8)
            sign_out_btn.Bind(wx.EVT_BUTTON, self._on_sign_out)
        add_btn = wx.Button(panel, wx.ID_ADD, label="Add / Replace Token...")
        add_btn.SetName("Add or Replace Token")
        btn_sizer.Add(add_btn)
        sizer.Add(btn_sizer, flag=wx.LEFT | wx.RIGHT, border=12)

        sizer.AddSpacer(8)
        close_btn = wx.Button(panel, wx.ID_OK, label="Done")
        close_btn.SetDefault()
        close_row = wx.BoxSizer(wx.HORIZONTAL)
        close_row.AddStretchSpacer()
        close_row.Add(close_btn)
        sizer.Add(close_row, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        add_btn.Bind(wx.EVT_BUTTON, self._on_add)

    def _on_sign_out(self, _event: object) -> None:
        self._removed = True
        self.dialog.EndModal(self._wx.ID_REMOVE)

    def _on_add(self, _event: object) -> None:
        self.dialog.EndModal(self._wx.ID_ADD)

    def show(self) -> str:
        """Return 'remove', 'add', or 'done'."""
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        try:
            result = show_modal_dialog(self.dialog, "Manage GitHub Accounts")
            if result == wx.ID_REMOVE:
                return "remove"
            if result == wx.ID_ADD:
                return "add"
            return "done"
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Repository browser dialog
# ---------------------------------------------------------------------------


class GitHubRepositoryBrowserDialog:
    """Browse a GitHub repository and select a file to open.

    Returns a :class:`~quill.core.github.models.BrowseResult` on success,
    or ``None`` if the user cancelled.
    """

    def __init__(
        self,
        parent: object,
        provider: GitHubRemoteProvider,
        identity_label: str,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._announce = announce_cb or (lambda _: None)
        self._repository: RemoteRepository | None = None
        self._current_ref = ""
        self._path_stack: list[str] = []  # stack of ancestor paths; top = current dir
        self._nodes: list[RemoteNode] = []
        self._refs: list[RemoteRef] = []
        # When the user clicks "Show all refs" we re-run list_refs with a
        # much higher cap.  ``_refs_truncated`` is True while the initial
        # list is still the cap'd version (finding #34).
        self._refs_truncated = False

        self.dialog = wx.Dialog(
            parent,
            title="GitHub Repository Browser",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((560, 420))
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Identity row
        id_row = wx.BoxSizer(wx.HORIZONTAL)
        id_label = wx.StaticText(panel, label="Account:")
        self._id_value = wx.StaticText(panel, label=identity_label)
        self._id_value.SetName("GitHub account")
        id_row.Add(id_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)
        id_row.Add(self._id_value, 1, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(id_row, flag=wx.EXPAND | wx.ALL, border=10)

        # Repository row
        repo_row = wx.BoxSizer(wx.HORIZONTAL)
        repo_label = wx.StaticText(panel, label="Repository (owner/repo):")
        self._repo_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._repo_ctrl.SetName("Repository in owner slash repo format")
        self._load_btn = wx.Button(panel, label="Load")
        self._load_btn.SetName("Load repository")
        repo_row.Add(repo_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)
        repo_row.Add(self._repo_ctrl, 1, wx.EXPAND | wx.RIGHT, border=6)
        repo_row.Add(self._load_btn)
        sizer.Add(repo_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # Branch/tag row
        ref_row = wx.BoxSizer(wx.HORIZONTAL)
        ref_label = wx.StaticText(panel, label="Branch or tag:")
        self._ref_choice = wx.Choice(panel, choices=[])
        self._ref_choice.SetName("Branch or tag")
        self._ref_choice.Enable(False)
        ref_row.Add(ref_label, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)
        ref_row.Add(self._ref_choice, 1, wx.EXPAND)
        sizer.Add(ref_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # Path breadcrumb
        self._path_label = wx.StaticText(panel, label="Path: /")
        self._path_label.SetName("Current path")
        sizer.Add(self._path_label, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # File list
        self._list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._list.SetName("Repository contents")
        self._list.InsertColumn(0, "Name", width=280)
        self._list.InsertColumn(1, "Type", width=70)
        self._list.InsertColumn(2, "Size", width=80)
        sizer.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # Status label
        self._status = wx.StaticText(panel, label="Enter a repository name and click Load.")
        self._status.SetName("Status")
        sizer.Add(self._status, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # Buttons
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._open_btn = wx.Button(panel, wx.ID_OK, label="Open File")
        self._open_btn.SetName("Open selected file")
        self._open_btn.Enable(False)
        self._go_up_btn = wx.Button(panel, label="Go Up")
        self._go_up_btn.SetName("Go up one folder")
        self._go_up_btn.Enable(False)
        self._refresh_btn = wx.Button(panel, label="Refresh")
        self._refresh_btn.SetName("Refresh current folder")
        self._refresh_btn.Enable(False)
        self._show_all_refs_btn = wx.Button(panel, label="Show all refs")
        self._show_all_refs_btn.SetName("Show all branches and tags")
        self._show_all_refs_btn.Enable(False)
        self._copy_url_btn = wx.Button(panel, label="Copy URL")
        self._copy_url_btn.SetName("Copy GitHub URL to clipboard")
        self._copy_url_btn.Enable(False)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_btn.SetName("Cancel")
        btn_row.Add(self._open_btn, flag=wx.RIGHT, border=6)
        btn_row.Add(self._go_up_btn, flag=wx.RIGHT, border=6)
        btn_row.Add(self._refresh_btn, flag=wx.RIGHT, border=6)
        btn_row.Add(self._show_all_refs_btn, flag=wx.RIGHT, border=6)
        btn_row.Add(self._copy_url_btn, flag=wx.RIGHT, border=6)
        btn_row.AddStretchSpacer()
        btn_row.Add(cancel_btn)
        sizer.Add(btn_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        # Event bindings
        self._load_btn.Bind(wx.EVT_BUTTON, self._on_load)
        self._repo_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_load)
        self._ref_choice.Bind(wx.EVT_CHOICE, self._on_ref_changed)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_item_activated)
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
        self._list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_item_deselected)
        self._open_btn.Bind(wx.EVT_BUTTON, self._on_open)
        self._go_up_btn.Bind(wx.EVT_BUTTON, self._on_go_up)
        self._refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        self._show_all_refs_btn.Bind(wx.EVT_BUTTON, self._on_show_all_refs)
        self._copy_url_btn.Bind(wx.EVT_BUTTON, self._on_copy_url)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)

    # ------------------------------------------------------------------
    # Public entry point

    def show(self) -> BrowseResult | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self._result: BrowseResult | None = None
        try:
            if show_modal_dialog(self.dialog, "GitHub Repository Browser") == wx.ID_OK:
                return self._result
            return None
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------
    # Event handlers

    def _on_load(self, _event: object) -> None:
        full_name = self._repo_ctrl.GetValue().strip()
        if not full_name:
            self._set_status("Enter a repository name (owner/repo) first.")
            return
        if "/" not in full_name:
            self._set_status("Repository must be in owner/repo format.")
            return
        self._set_loading(True)
        self._set_status(f"Loading {full_name}...")
        threading.Thread(  # GATE-40-OK: GitHub repo loader; bounded by LIST_REFS_INITIAL_LIMIT.
            target=self._load_repo_worker,
            args=(full_name, LIST_REFS_INITIAL_LIMIT),
            daemon=True,
        ).start()

    def _on_show_all_refs(self, _event: object) -> None:
        if not self._repository:
            return
        self._set_loading(True)
        self._set_status("Loading all branches and tags...")
        threading.Thread(  # GATE-40-OK: full-refs loader; bounded by LIST_REFS_FULL_LIMIT.
            target=self._load_repo_worker,
            args=(self._repository.full_name, LIST_REFS_FULL_LIMIT),
            daemon=True,
        ).start()

    def _on_ref_changed(self, _event: object) -> None:
        idx = self._ref_choice.GetSelection()
        if idx < 0 or idx >= len(self._refs):
            return
        self._current_ref = self._refs[idx].name
        self._path_stack.clear()
        self._load_directory("")

    def _on_item_activated(self, event: object) -> None:
        idx = getattr(event, "Index", -1) if hasattr(event, "Index") else -1
        if idx < 0 or idx >= len(self._nodes):
            return
        node = self._nodes[idx]
        if node.kind == "dir":
            self._path_stack.append(node.path)
            self._load_directory(node.path)
        else:
            self._do_open(node)

    def _on_item_selected(self, _event: object) -> None:
        self._update_open_button()

    def _on_item_deselected(self, _event: object) -> None:
        self._update_open_button()

    def _on_open(self, _event: object) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0 or idx >= len(self._nodes):
            return
        node = self._nodes[idx]
        if node.kind == "dir":
            self._path_stack.append(node.path)
            self._load_directory(node.path)
        else:
            self._do_open(node)

    def _on_go_up(self, _event: object) -> None:
        if self._path_stack:
            self._path_stack.pop()
        parent_path = self._path_stack[-1] if self._path_stack else ""
        self._load_directory(parent_path)

    def _on_refresh(self, _event: object) -> None:
        current = self._path_stack[-1] if self._path_stack else ""
        self._load_directory(current)

    def _on_copy_url(self, _event: object) -> None:
        if not self._repository:
            return
        idx = self._list.GetFirstSelected()
        if 0 <= idx < len(self._nodes):
            node = self._nodes[idx]
            url = (
                f"https://github.com/{self._repository.full_name}"
                f"/blob/{self._current_ref}/{node.path}"
            )
        else:
            url = self._repository.html_url
        wx = self._wx
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(url))
            wx.TheClipboard.Close()
        self._set_status(f"URL copied: {url}")

    def _on_key(self, event: object) -> None:
        wx = self._wx
        key = getattr(event, "GetKeyCode", lambda: 0)()
        focused = wx.Window.FindFocus()
        if key == wx.WXK_F5:
            self._on_refresh(None)
        elif key == wx.WXK_BACK:
            # Only treat Backspace as "Go Up" when the list control has focus.
            # If the repo field or any TextCtrl has focus, let it delete characters.
            if self._path_stack and focused is self._list:
                self._on_go_up(None)
            else:
                event.Skip()  # type: ignore[union-attr]
        else:
            event.Skip()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Workers and UI updates

    def _load_repo_worker(self, full_name: str, limit: int) -> None:
        wx = self._wx
        try:
            repo = self._provider.get_repository(full_name)
            refs = self._provider.list_refs(repo, limit=limit)
            wx.CallAfter(self._on_repo_loaded, repo, refs, limit)
        except Exception as exc:  # noqa: BLE001
            wx.CallAfter(self._on_load_error, str(exc))

    def _on_repo_loaded(
        self,
        repo: RemoteRepository,
        refs: list[RemoteRef],
        limit: int,
    ) -> None:
        self._repository = repo
        self._refs = refs
        # "Show all refs" stays available only while we have a capped list
        # (the dialog was opened with the default small cap) so the user
        # can opt into the full pull.
        self._refs_truncated = limit <= LIST_REFS_INITIAL_LIMIT
        self._ref_choice.Clear()
        for ref in refs:
            label = f"{ref.name} ({ref.kind})"
            self._ref_choice.Append(label)
        if not refs:
            self._set_loading(False)
            self._set_status(
                f"{repo.full_name} has no branches. "
                "It may be an empty repository. Press Cancel to go back."
            )
            return
        default_idx = next(
            (i for i, r in enumerate(refs) if r.name == repo.default_branch),
            0,
        )
        self._ref_choice.SetSelection(default_idx)
        self._ref_choice.Enable(True)
        self._current_ref = refs[default_idx].name
        self._path_stack.clear()
        desc = f" — {repo.description}" if repo.description else ""
        if self._refs_truncated:
            self._show_all_refs_btn.Enable(True)
            self._set_status(
                f"Loaded {repo.full_name}{desc}. Showing first {len(refs)} "
                "refs; click 'Show all refs' for the full list."
            )
        else:
            self._show_all_refs_btn.Enable(False)
            self._set_status(f"Loaded {repo.full_name}{desc}.")
        self._load_directory("")

    def _on_load_error(self, message: str) -> None:
        self._set_loading(False)
        self._set_status(f"Error: {message}")

    def _load_directory(self, path: str) -> None:
        if not self._repository or not self._current_ref:
            return
        self._set_loading(True)
        display_path = "/" + path if path else "/"
        self._path_label.SetLabel(f"Path: {display_path}")
        self._set_status(f"Loading {display_path}...")
        threading.Thread(  # GATE-40-OK: directory listing worker; bounded by API page size.
            target=self._load_dir_worker,
            args=(self._repository, path, self._current_ref),
            daemon=True,
        ).start()

    def _load_dir_worker(
        self,
        repo: RemoteRepository,
        path: str,
        ref: str,
    ) -> None:
        wx = self._wx
        try:
            nodes = self._provider.list_directory(repo, path, ref)
            wx.CallAfter(self._on_dir_loaded, nodes, path)
        except Exception as exc:  # noqa: BLE001
            wx.CallAfter(self._on_load_error, str(exc))

    def _on_dir_loaded(self, nodes: list[RemoteNode], path: str) -> None:
        self._nodes = nodes
        self._list.DeleteAllItems()
        for node in nodes:
            idx = self._list.InsertItem(self._list.GetItemCount(), node.name)
            self._list.SetItem(idx, 1, "Folder" if node.kind == "dir" else "File")
            if node.kind == "file" and node.size:
                size_kb = node.size / 1024
                self._list.SetItem(idx, 2, f"{size_kb:.1f} KB")
        self._set_loading(False)
        self._go_up_btn.Enable(bool(self._path_stack))
        display_path = "/" + path if path else "/"
        count = len(nodes)
        self._set_status(f"{count} item{'s' if count != 1 else ''} in {display_path}")
        self._update_open_button()
        # Focus the list and select the first item so SR users know content arrived.
        if count > 0:
            self._list.SetFocus()
            self._list.Select(0)
            self._list.Focus(0)

    def _do_open(self, node: RemoteNode) -> None:
        if not self._repository:
            return
        from quill.core.github.models import BrowseResult

        self._result = BrowseResult(
            repository=self._repository,
            path=node.path,
            ref=self._current_ref,
            sha=node.sha,
            html_url=(
                f"https://github.com/{self._repository.full_name}"
                f"/blob/{self._current_ref}/{node.path}"
            ),
        )
        self.dialog.EndModal(self._wx.ID_OK)

    def _set_loading(self, loading: bool) -> None:
        self._load_btn.Enable(not loading)
        self._repo_ctrl.Enable(not loading)
        self._refresh_btn.Enable(not loading and bool(self._repository))
        if loading:
            self._open_btn.Enable(False)
        self._go_up_btn.Enable(not loading and bool(self._path_stack))

    def _update_open_button(self) -> None:
        idx = self._list.GetFirstSelected()
        file_selected = 0 <= idx < len(self._nodes) and self._nodes[idx].kind == "file"
        self._open_btn.Enable(file_selected)
        self._copy_url_btn.Enable(bool(self._repository) and idx >= 0)

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        self._status.GetParent().Layout()
        if message:
            self._announce(message)
