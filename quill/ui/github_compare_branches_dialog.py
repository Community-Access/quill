"""Compare Branches: ahead/behind counts, commits, and changed files between
two branches (GHManage parity, Ctrl+Shift+B).

Opened from :class:`~quill.ui.github_items_dialog.GitHubItemsDialog`'s
Branches view with an already-fetched
:class:`~quill.core.github.items_provider.GitHubBranchComparison` -- the same
fetch-then-open pattern already used for the PR diff viewer's
``_show_diff_dialog``. Two pages: Commits (a plain list) and Changed Files
(a list-over-detail pane that renders each file's differences through
QUILL's own compare engine, the same rendering
:class:`~quill.ui.github_pr_diff_dialog.GitHubPullDiffDialog` uses for a pull
request -- fetched here at the two branch names as refs rather than a PR's
base/head shas).
"""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING

from quill.core.github.items_provider import GitHubBranchComparison, GitHubItemsError
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.github_items_view import pull_diff_file_label, render_pull_file_diff

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider


class GitHubCompareBranchesDialog:
    """Modal viewer for the ahead/behind/commits/files between two branches."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        repo: str,
        comparison: GitHubBranchComparison,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._comparison = comparison
        self._announce = announce_cb or (lambda _m: None)
        self._load_token = 0  # invalidates stale content workers on reselect

        self.dialog = wx.Dialog(
            parent,
            title=f"Compare {comparison.base}...{comparison.head}"[:120],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((680, 480))
        self.dialog.SetSize((820, 600))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(panel, label=self._summary_line())
        summary.SetName("Comparison summary")
        summary.Wrap(780)
        root.Add(summary, 0, wx.ALL, 8)

        notebook = wx.Notebook(panel)
        notebook.SetName("Comparison detail")

        commits_panel = wx.Panel(notebook)
        commits_sizer = wx.BoxSizer(wx.VERTICAL)
        self._commits_list = wx.ListCtrl(commits_panel, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._commits_list.SetName(f"Commits between {comparison.base} and {comparison.head}")
        for i, col in enumerate(("SHA", "Author", "Date", "Message")):
            self._commits_list.InsertColumn(i, col, width=170 if col == "Message" else 110)
        for commit in comparison.commits:
            idx = self._commits_list.InsertItem(self._commits_list.GetItemCount(), commit.short_sha)
            self._commits_list.SetItem(idx, 1, commit.author)
            self._commits_list.SetItem(idx, 2, commit.date[:10])
            message = commit.message.splitlines()[0] if commit.message else ""
            self._commits_list.SetItem(idx, 3, message)
        commits_sizer.Add(self._commits_list, 1, wx.EXPAND | wx.ALL, 6)
        commits_panel.SetSizer(commits_sizer)
        notebook.AddPage(commits_panel, f"Commits ({len(comparison.commits)})")

        files_panel = wx.Panel(notebook)
        files_sizer = wx.BoxSizer(wx.VERTICAL)
        self._files = wx.ListBox(
            files_panel, choices=[pull_diff_file_label(f) for f in comparison.files]
        )
        self._files.SetName("Changed files; select one to hear its differences")
        files_sizer.Add(self._files, 1, wx.EXPAND | wx.ALL, 6)
        files_sizer.Add(wx.StaticText(files_panel, label="Differences"), 0, wx.LEFT | wx.TOP, 6)
        self._detail = wx.TextCtrl(
            files_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.TE_RICH2
        )
        self._detail.SetName(
            f"Differences for the selected file, {comparison.base} vs {comparison.head}"
        )
        files_sizer.Add(self._detail, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        files_panel.SetSizer(files_sizer)
        notebook.AddPage(files_panel, f"Changed Files ({len(comparison.files)})")

        root.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._browser_btn = wx.Button(panel, label="Open on &GitHub")
        self._browser_btn.SetName("Open this comparison on GitHub in your browser")
        self._browser_btn.Enable(bool(comparison.permalink_url))
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close comparison")
        btn_row.Add(self._browser_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._files.Bind(wx.EVT_LISTBOX, self._on_select_file)
        self._browser_btn.Bind(wx.EVT_BUTTON, self._on_open_browser)

    def _summary_line(self) -> str:
        c = self._comparison
        if c.status == "identical":
            return f"{c.head} is identical to {c.base}."
        return (
            f"{c.head} is {c.ahead_by} commit(s) ahead and {c.behind_by} behind {c.base}. "
            f"{c.total_commits} total commit(s), {len(c.files)} changed file(s)."
        )

    def show(self) -> None:
        wx = self._wx
        if self._comparison.files:
            self._files.SetSelection(0)
            self._on_select_file(None)
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
            show_modal_dialog(self.dialog, "Compare Branches", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------

    def _on_open_browser(self, _event: object) -> None:
        if self._comparison.permalink_url:
            webbrowser.open(self._comparison.permalink_url)
            self._announce("Opened comparison in browser")

    def _on_select_file(self, _event: object) -> None:
        index = self._files.GetSelection()
        if index < 0 or index >= len(self._comparison.files):
            return
        pull_file = self._comparison.files[index]
        self._load_token += 1
        token = self._load_token
        self._detail.SetValue(f"Comparing {pull_file.filename}...")
        base = self._comparison.base
        head = self._comparison.head

        def worker() -> None:
            wx = self._wx
            try:
                base_text = (
                    ""
                    if pull_file.status == "added"
                    else self._provider.fetch_file_text(
                        self._repo, pull_file.previous_filename or pull_file.filename, base
                    )
                )
                head_text = (
                    ""
                    if pull_file.status == "removed"
                    else self._provider.fetch_file_text(self._repo, pull_file.filename, head)
                )
                text = render_pull_file_diff(
                    pull_file.filename, base_text, head_text, base_label=base, head_label=head
                )
            except GitHubItemsError as exc:
                # Binary / oversized content: fall back to the counts + patch.
                fallback = [f"{pull_file.filename}: {exc}"]
                fallback.append(f"+{pull_file.additions} -{pull_file.deletions} lines changed.")
                if pull_file.patch:
                    fallback.append("")
                    fallback.append("GitHub's unified patch:")
                    fallback.append(pull_file.patch)
                text = "\n".join(fallback)
            except Exception as exc:  # noqa: BLE001 - report, never crash the dialog
                text = f"Could not compare {pull_file.filename}: {exc}"
            wx.CallAfter(self._on_diff_ready, token, text)

        threading.Thread(  # GATE-40-OK: per-file content fetch + compare.
            target=worker, daemon=True
        ).start()

    def _on_diff_ready(self, token: int, text: str) -> None:
        if token != self._load_token:
            return  # the user already moved to a different file
        self._detail.SetValue(text)
        first_line = text.splitlines()[0] if text else "No differences"
        self._announce(first_line)


__all__ = ["GitHubCompareBranchesDialog"]
