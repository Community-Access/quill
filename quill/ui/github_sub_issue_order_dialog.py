"""Reorder Sub-issues: move one of a parent issue's sub-issues up or down.

Opened from the GitHub Items viewer's context menu on an issue that has
sub-issues (QUILL and QUILL Lite share it). Move Up (Alt+U) and Move Down
(Alt+D) send GitHub one ``PATCH .../sub_issues/priority`` each; the list is
then read back from GitHub, so what it shows is the order GitHub holds, and
QUILL says where the sub-issue landed ("#12 is now 2 of 5"). Enter opens the
selected sub-issue in the browser.
"""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING, Any

from quill.core.github.items_errors import GitHubItemsError
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.issue_housekeeping import GitHubIssueHousekeeping, SubIssue

__all__ = ["SubIssueOrderDialog"]


class SubIssueOrderDialog:
    """A list of sub-issues in GitHub's order, with Move Up and Move Down."""

    def __init__(
        self,
        parent: object,
        housekeeping: GitHubIssueHousekeeping,
        *,
        repo: str,
        parent_number: int,
        order: list[SubIssue],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._housekeeping = housekeeping
        self._repo = repo
        self._parent_number = parent_number
        self._order = list(order)
        self._announce = announce_cb or (lambda _message: None)
        self._busy = False
        self._token = 0
        self.dialog = wx.Dialog(
            parent,
            title=f"Reorder Sub-issues of #{parent_number}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 460, 360))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(panel, label="&Sub-issues, in order:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(panel, choices=[item.label for item in self._order])
        self._list.SetName("Sub-issues, in GitHub's order")
        self._list.SetHelpText(
            "The parent issue's sub-issues, first to last. Move Up and Move Down change the "
            "selected one's place on GitHub; Enter opens it in your browser."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._up = wx.Button(panel, label="Move &Up")
        self._up.SetHelpText("Moves the selected sub-issue one place earlier, on GitHub.")
        self._down = wx.Button(panel, label="Move &Down")
        self._down.SetHelpText("Moves the selected sub-issue one place later, on GitHub.")
        close = wx.Button(panel, wx.ID_CANCEL, "Close")
        close.SetHelpText("Closes this window. Every move has already been sent.")
        row.Add(self._up, 0, wx.RIGHT, 6)
        row.Add(self._down, 0, wx.RIGHT, 6)
        row.AddStretchSpacer()
        row.Add(close)
        root.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Reorder status")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.SetSize(dip_size(self.dialog, 540, 420))
        self._up.Bind(wx.EVT_BUTTON, lambda _event: self._move(-1))
        self._down.Bind(wx.EVT_BUTTON, lambda _event: self._move(1))
        apply_listbox_activation(self._list, self._open_selected)
        bind_close_button(self.dialog, close, modeless=False)
        if self._order:
            self._list.SetSelection(0)
        self._list.SetFocus()

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, self.dialog.GetTitle(), announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _open_selected(self, _event: object) -> None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._order):
            item = self._order[index]
            url = item.url or f"https://github.com/{self._repo}/issues/{item.number}"
            self._announce("Opened on GitHub." if webbrowser.open(url) else "Could not open it.")

    def _move(self, delta: int) -> None:
        index = self._list.GetSelection()
        if not 0 <= index < len(self._order):
            self._say("Select a sub-issue first.")
            return
        if self._busy:
            self._say("Wait for the last move to finish.")
            return
        moving = self._order[index]
        self._busy = True
        self._token += 1
        token = self._token
        self._status.SetLabel(f"Moving #{moving.number}...")

        def worker() -> None:
            result: Any
            try:
                result = self._housekeeping.move_sub_issue(
                    self._repo, self._parent_number, self._order, index, delta
                )
            except GitHubItemsError as exc:
                result = exc
            except Exception as exc:  # noqa: BLE001 - say any failure
                result = GitHubItemsError(f"Could not move #{moving.number}: {exc}")
            self._wx.CallAfter(self._moved, token, moving.id, moving.number, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: GitHub write.

    def _moved(self, token: int, moved_id: int, number: int, result: Any) -> None:
        if token != self._token or not dialog_alive(self.dialog):
            return
        self._busy = False
        if isinstance(result, GitHubItemsError):
            self._say(str(result.args[0]) if result.args else str(result))
            return
        self._order = list(result)
        self._list.Set([item.label for item in self._order])
        place = next((i for i, item in enumerate(self._order) if item.id == moved_id), -1)
        if place >= 0:
            self._list.SetSelection(place)
            self._say(f"#{number} is now {place + 1} of {len(self._order)}.")
        else:
            self._say(f"GitHub moved #{number}, but it is no longer listed. Refresh to check.")
