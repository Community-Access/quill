"""Accessible PR diff viewer: a pull request's files through QUILL's compare.

Unified GitHub Management, "PR Diff Viewer": a modal list-over-detail dialog —
one row per changed file, and the selected file's changes rendered by QUILL's
own compare engine (:mod:`quill.core.compare_service`) as the same spoken
difference walk Compare Documents gives ("Difference 2 of 5. Text changed at
line 41. base: ... this PR: ..."), never a raw unified patch.

Content for both sides is fetched off-thread through the provider
(``fetch_file_text`` at the PR's base/head shas); binary and over-1MB files
degrade to the file's own +/- counts and GitHub's patch text when present.
Read-only; same conventions as the parent GitHub Items dialog
(``show_modal_dialog``, every control named, GATE-40 threads via CallAfter).
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.items_provider import GitHubItemsError, GitHubPullDiff
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.github_items_view import pull_diff_file_label, render_pull_file_diff

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider


class GitHubPullDiffDialog:
    """Modal viewer for one PR's changed files, compared accessibly."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        repo: str,
        diff: GitHubPullDiff,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._diff = diff
        self._announce = announce_cb or (lambda _m: None)
        self._load_token = 0  # invalidates stale content workers on reselect

        self.dialog = wx.Dialog(
            parent,
            title=f"PR #{diff.number} diff: {diff.title}"[:120],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((680, 480))
        self.dialog.SetSize((820, 600))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        summary = (
            f"{len(diff.files)} changed file{'s' if len(diff.files) != 1 else ''}, "
            f"{diff.head_ref or 'head'} into {diff.base_ref or 'base'}"
        )
        header = wx.StaticText(panel, label=summary)
        header.SetName("Pull request summary")
        root.Add(header, 0, wx.ALL, 8)

        self._files = wx.ListBox(panel, choices=[pull_diff_file_label(f) for f in diff.files])
        self._files.SetName("Changed files; select one to hear its differences")
        root.Add(self._files, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="Differences"), 0, wx.LEFT | wx.TOP, 8)
        self._detail = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.TE_RICH2
        )
        self._detail.SetName("Differences for the selected file, spoken the Compare Documents way")
        root.Add(self._detail, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close diff viewer")
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        self.dialog.SetSizer(root)
        self._files.Bind(wx.EVT_LISTBOX, self._on_select)

    def show(self) -> None:
        wx = self._wx
        if self._diff.files:
            self._files.SetSelection(0)
            self._on_select(None)
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
            show_modal_dialog(self.dialog, "PR Diff", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------

    def _on_select(self, _event: object) -> None:
        index = self._files.GetSelection()
        if index < 0 or index >= len(self._diff.files):
            return
        pull_file = self._diff.files[index]
        self._load_token += 1
        token = self._load_token
        self._detail.SetValue(f"Comparing {pull_file.filename}...")

        def worker() -> None:
            wx = self._wx
            try:
                base_text = (
                    ""
                    if pull_file.status == "added"
                    else self._provider.fetch_file_text(
                        self._repo,
                        pull_file.previous_filename or pull_file.filename,
                        self._diff.base_sha,
                    )
                )
                head_text = (
                    ""
                    if pull_file.status == "removed"
                    else self._provider.fetch_file_text(
                        self._repo, pull_file.filename, self._diff.head_sha
                    )
                )
                text = render_pull_file_diff(
                    pull_file.filename,
                    base_text,
                    head_text,
                    base_label=self._diff.base_ref or "base",
                    head_label=self._diff.head_ref or "this PR",
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


__all__ = ["GitHubPullDiffDialog"]
