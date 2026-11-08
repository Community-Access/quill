"""A commit's comments, and a new one on the whole commit or on a file line.

Reached from a commit row in the GitHub Items viewer (Commits view, or a
branch's commits), by the context menu's Commit Comments. Each comment reads as
author, date and text; Tab reaches the whole comment. A new comment goes on the
whole commit unless a file is named, and on one line of that file when a line
number is given too. The list and the post run off the UI thread, a slow list
cannot land over a newer one, and "posted" is said only when GitHub returned
the comment. QUILL and QUILL Lite share this window, as they share the viewer.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from quill.core.github.commit_comments import CommitComment
from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

__all__ = ["GitHubCommitCommentsDialog"]


def _words(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


class GitHubCommitCommentsDialog:
    """List a commit's comments and post a new one."""

    def __init__(
        self,
        parent: object,
        provider: Any,
        repo: str,
        sha: str,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._sha = sha
        self._announce = announce_cb or (lambda _message: None)
        self._comments: tuple[CommitComment, ...] = ()
        self._generation = 0
        self._posting = False
        self.dialog = wx.Dialog(
            parent,
            title=f"Comments on commit {sha[:7]} in {repo}"[:120],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 480))
        self.dialog.SetSize(dip_size(self.dialog, 760, 620))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(panel, label="&Comments:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName("Commit comments")
        self._list.SetHelpText(
            "Each comment as its author, date and first line. Tab reads the whole "
            "comment; Enter moves there."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(wx.StaticText(panel, label="Selected co&mment:"), 0, wx.LEFT | wx.RIGHT, 8)
        self._detail = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._detail.SetName("Selected commit comment")
        self._detail.SetHelpText("The whole comment: who wrote it, when, where, and its text.")
        root.Add(self._detail, 1, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(panel, label="&New comment:"), 0, wx.LEFT | wx.RIGHT, 8)
        self._body = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
        self._body.SetName("New commit comment")
        self._body.SetHelpText("The text of your comment. Markdown works, as it does on GitHub.")
        root.Add(self._body, 1, wx.EXPAND | wx.ALL, 8)
        place = wx.BoxSizer(wx.HORIZONTAL)
        place.Add(
            wx.StaticText(panel, label="&File, optional:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            5,
        )
        self._path = wx.TextCtrl(panel)
        self._path.SetName("File the comment is on, optional")
        self._path.SetHelpText(
            "Leave empty to comment on the whole commit, or type a path the commit "
            "changed, such as docs/readme.md."
        )
        place.Add(self._path, 2, wx.RIGHT, 10)
        place.Add(
            wx.StaticText(panel, label="&Line, optional:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            5,
        )
        self._line = wx.TextCtrl(panel)
        self._line.SetName("Line number the comment is on, optional")
        self._line.SetHelpText(
            "A line number in that file, from 1 up. Leave empty to comment on the file as a whole."
        )
        place.Add(self._line, 1)
        root.Add(place, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._status = wx.StaticText(panel, label="Loading comments from GitHub...")
        self._status.SetName("Commit comments status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._post_btn = wx.Button(panel, label="&Post Comment")
        self._post_btn.SetHelpText(
            "Send the new comment to GitHub. QUILL says posted only when GitHub returns it."
        )
        self._refresh_btn = wx.Button(panel, label="&Refresh")
        self._refresh_btn.SetHelpText("Read the commit's comments from GitHub again.")
        close_btn = wx.Button(panel, wx.ID_CANCEL, label="Close")
        close_btn.SetHelpText("Close the commit comments.")
        buttons.Add(self._post_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._refresh_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._list.Bind(wx.EVT_LISTBOX, self._select)
        apply_listbox_activation(self._list, lambda _event: self._detail.SetFocus())
        self._post_btn.Bind(wx.EVT_BUTTON, self._post)
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _event: self._load())
        bind_close_button(self.dialog, close_btn, modeless=False)
        self._post_btn.Enable(bool(getattr(provider, "is_authenticated", False)))

    # -- Reading -----------------------------------------------------------

    def _load(self) -> None:
        self._generation += 1
        generation = self._generation
        self._status.SetLabel("Loading comments from GitHub...")

        def worker() -> None:
            try:
                result: Any = self._provider.fetch_commit_comments(self._repo, self._sha)
            except GitHubItemsError as exc:
                result = exc
            except Exception as exc:  # noqa: BLE001 - say it rather than lose it
                result = GitHubItemsError(f"Unexpected error: {exc}")
            self._wx.CallAfter(self._loaded, generation, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: comment read.

    def _loaded(self, generation: int, result: Any) -> None:
        if generation != self._generation or not dialog_alive(self.dialog):
            return
        if isinstance(result, GitHubItemsError):
            message = f"Could not load the comments. {_words(result)}"
            self._status.SetLabel(message)
            self._announce(message)
            return
        self._comments = tuple(result.items)
        self._list.Set([comment.label() for comment in self._comments])
        count = len(self._comments)
        message = (
            f"{count} comment{'s' if count != 1 else ''} on this commit."
            if count
            else "No comments on this commit yet."
        )
        if result.warning:
            message += f" {result.warning}"
        self._status.SetLabel(message)
        self._announce(message)
        if self._comments:
            self._list.SetSelection(0)
            self._select(None)
        else:
            self._detail.SetValue("")

    def _select(self, _event: object) -> None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._comments):
            self._detail.SetValue(self._comments[index].detail())

    # -- Posting -----------------------------------------------------------

    def _post(self, _event: object) -> None:
        if self._posting:
            self._announce("Wait for the comment you sent to finish.")
            return
        body = self._body.GetValue()
        path = self._path.GetValue().strip()
        line_text = self._line.GetValue().strip()
        if not body.strip():
            self._refuse("Type the comment first.", self._body)
            return
        line: int | None = None
        if line_text:
            if not line_text.isdecimal() or int(line_text) <= 0:
                self._refuse("The line is a number from 1 up, or empty.", self._line)
                return
            if not path:
                self._refuse("Name the file the line is in, or clear the line.", self._path)
                return
            line = int(line_text)
        self._posting = True
        self._status.SetLabel("Sending the comment to GitHub...")

        def worker() -> None:
            try:
                result: Any = self._provider.add_commit_comment(
                    self._repo, self._sha, body, path=path, line=line
                )
            except GitHubItemsError as exc:
                result = exc
            except Exception as exc:  # noqa: BLE001 - say it rather than lose it
                result = GitHubItemsError(f"Unexpected error: {exc}")
            self._wx.CallAfter(self._posted, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented write.

    def _posted(self, result: Any) -> None:
        if not dialog_alive(self.dialog):
            return
        self._posting = False
        if isinstance(result, GitHubItemsError):
            message = _words(result)
            self._status.SetLabel(message)
            self._announce(message)
            return
        self._body.SetValue("")
        message = f"Comment posted on {result.where}."
        self._status.SetLabel(message)
        self._announce(message)
        self._load()

    def _refuse(self, message: str, field: Any) -> None:
        self._status.SetLabel(message)
        self._announce(message)
        field.SetFocus()

    def show(self) -> None:
        wx = self._wx
        self._load()
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        self._list.SetFocus()
        try:
            show_modal_dialog(self.dialog, "Commit Comments", announce=self._announce)
        finally:
            self.dialog.Destroy()
