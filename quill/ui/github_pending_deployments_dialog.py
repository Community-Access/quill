"""Review a workflow run's pending deployments: approve or reject, with a comment.

A run that deploys to a protected environment stops and waits for a reviewer.
This window lists the environments it is waiting on, checks the ones this
account may approve, and sends the choice with the comment GitHub requires.
It says only what GitHub confirmed: the environments named in its reply.
Shared by QUILL and QUILL Lite through the GitHub Items viewer.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider
    from quill.core.github.run_actions import PendingDeployment

__all__ = ["PendingDeploymentsDialog"]


class PendingDeploymentsDialog:
    """Environments one run is waiting on, with Approve and Reject."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        repo: str,
        run_id: int,
        run_label: str,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._run_id = run_id
        self._run_label = run_label
        self._announce = announce_cb or (lambda _message: None)
        self._pending: tuple[PendingDeployment, ...] = ()
        self._token = 0
        self._busy = False
        self.dialog = wx.Dialog(
            parent,
            title=f"Pending Deployments: {run_label}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 420))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        env_label = wx.StaticText(panel, label="&Environments waiting for review")
        env_label.SetHelpText("The environments this run is waiting on.")
        root.Add(env_label, 0, wx.ALL, 8)
        # One real check box per environment (A11Y-SR-1): a CheckListBox's checked
        # state is not announced as you arrow through it.
        self._envs = wx.ScrolledWindow(panel, style=wx.VSCROLL | wx.TAB_TRAVERSAL)
        self._envs.SetName("Environments waiting for review")
        self._envs.SetHelpText(
            "One check box per environment. The ones you are allowed to approve start "
            "checked; GitHub refuses the others."
        )
        self._envs.SetScrollRate(0, self.dialog.FromDIP(10))
        self._env_sizer = wx.BoxSizer(wx.VERTICAL)
        self._envs.SetSizer(self._env_sizer)
        self._env_boxes: list[object] = []
        root.Add(self._envs, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        comment_label = wx.StaticText(panel, label="&Comment (GitHub requires one)")
        comment_label.SetHelpText("The comment GitHub records with your review.")
        root.Add(comment_label, 0, wx.ALL, 8)
        self._comment = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        self._comment.SetName("Review comment")
        self._comment.SetHelpText(
            "Say why you approve or reject. GitHub records it on the run and requires it."
        )
        root.Add(self._comment, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="Loading pending deployments...")
        self._status.SetName("Pending deployments status")
        self._status.SetHelpText("Says what is loading and what GitHub confirmed.")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._approve_btn = wx.Button(panel, label="&Approve")
        self._approve_btn.SetName("Approve the checked environments")
        self._approve_btn.SetHelpText("Lets the run deploy to the checked environments.")
        self._reject_btn = wx.Button(panel, label="&Reject")
        self._reject_btn.SetName("Reject the checked environments")
        self._reject_btn.SetHelpText("Stops the run deploying to the checked environments.")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close pending deployments")
        close_btn.SetHelpText("Close this window without reviewing.")
        buttons.Add(self._approve_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._reject_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.SetSize(dip_size(self.dialog, 640, 480))
        self._approve_btn.Bind(wx.EVT_BUTTON, lambda _event: self._review(True))
        self._reject_btn.Bind(wx.EVT_BUTTON, lambda _event: self._review(False))
        bind_close_button(self.dialog, close_btn, modeless=False)
        self._set_enabled(False)

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
        try:
            show_modal_dialog(self.dialog, "Pending Deployments", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _set_enabled(self, enabled: bool) -> None:
        self._approve_btn.Enable(enabled)
        self._reject_btn.Enable(enabled)

    def _load(self) -> None:
        self._token += 1
        token = self._token
        self._set_enabled(False)

        def worker() -> None:
            try:
                pending = self._provider.fetch_pending_deployments(self._repo, self._run_id)
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._loaded, token, (), str(exc))
                return
            self._wx.CallAfter(self._loaded, token, pending, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: pending read.

    def _loaded(self, token: int, pending: tuple[PendingDeployment, ...], error: str) -> None:
        if token != self._token or not dialog_alive(self.dialog):
            return
        self._pending = pending
        wx = self._wx
        for box in self._env_boxes:
            box.Destroy()
        self._env_boxes = []
        for item in pending:
            box = wx.CheckBox(self._envs, label=item.label)
            box.SetValue(item.can_approve)
            box.SetHelpText("Checked, Approve or Reject applies to this environment.")
            self._env_sizer.Add(box, 0, wx.ALL, 4)
            self._env_boxes.append(box)
        self._envs.FitInside()
        if error:
            message = f"Could not load pending deployments: {error}"
        elif not pending:
            message = "This run is not waiting on any deployment review."
        else:
            mine = sum(1 for item in pending if item.can_approve)
            message = f"{len(pending)} environment(s) waiting; you can approve {mine}."
        self._status.SetLabel(message)
        self._announce(message)
        self._set_enabled(bool(pending))

    def _checked(self) -> list[PendingDeployment]:
        return [
            item for index, item in enumerate(self._pending) if self._env_boxes[index].GetValue()
        ]

    def _review(self, approve: bool) -> None:
        verb = "approve" if approve else "reject"
        if self._busy:
            self._announce("Wait for GitHub to answer the last review.")
            return
        chosen = self._checked()
        if not chosen:
            self._announce(f"Check at least one environment to {verb}.")
            if self._env_boxes:
                self._env_boxes[0].SetFocus()
            return
        comment = self._comment.GetValue().strip()
        if not comment:
            self._announce("Write a comment first; GitHub requires one.")
            self._comment.SetFocus()
            return
        names = ", ".join(item.environment for item in chosen)
        wx = self._wx
        question = f"{verb.capitalize()} deployment of {self._run_label} to {names}?" + (
            "" if approve else " The run will not deploy there."
        )
        with wx.MessageDialog(
            self.dialog, question, f"{verb.capitalize()} Deployment", wx.YES_NO | wx.NO_DEFAULT
        ) as box:
            if (
                show_modal_dialog(box, f"{verb.capitalize()} Deployment", announce=self._announce)
                != wx.ID_YES
            ):
                return
        self._busy = True
        self._set_enabled(False)
        ids = [item.environment_id for item in chosen]

        def worker() -> None:
            try:
                confirmed = self._provider.review_pending_deployments(
                    self._repo, self._run_id, ids, approve=approve, comment=comment
                )
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._reviewed, str(exc), approve, ())
                return
            self._wx.CallAfter(self._reviewed, "", approve, confirmed)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: consented review.

    def _reviewed(self, error: str, approve: bool, confirmed: tuple[str, ...]) -> None:
        if not dialog_alive(self.dialog):
            return
        self._busy = False
        if error:
            self._status.SetLabel(error)
            self._announce(error)
            self._set_enabled(bool(self._pending))
            return
        done = "Approved" if approve else "Rejected"
        named = ", ".join(confirmed) if confirmed else "the checked environments"
        message = f"{done} by GitHub: {named}."
        self._comment.SetValue("")
        self._status.SetLabel(message)
        self._announce(message)
        self._load()
