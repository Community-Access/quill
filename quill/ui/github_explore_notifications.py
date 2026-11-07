"""Notifications triage in Explore's notifications view (QUILL and QUILL Lite).

Mark Done, Unsubscribe, Mark All Read and an Include Read check box sit under
the results list and only show in the notifications view. Done and Unsubscribe
take the row out of the list and leave the cursor on the next row, so working
down an inbox is Delete, Delete, Delete without hunting for your place. Enter
on a row marks it read and opens it in QUILL's own view when there is one: a
pull request opens in Review, an issue in the GitHub Items viewer, and
anything else in the browser.

The core rules (reason wording, poll interval, where the cursor goes) live in
:mod:`quill.core.github.notification_triage`; this module only shows them.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.explore import ExploreRow, GitHubExploreError
from quill.core.github.fetch_results import GitHubFetchResult
from quill.core.github.notification_triage import notification_row, selection_after_removal
from quill.core.github.references import GitHubReferenceError, parse_github_reference
from quill.ui.dialog_contract import dialog_alive

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["GitHubExploreNotificationsMixin"]


class GitHubExploreNotificationsMixin:
    """Triage controls and actions for the Explore notifications view."""

    def _build_notification_controls(self, panel: object, root: object) -> None:
        wx = self._wx
        self._notification_panel = panel
        self._notification_root = root
        self._notification_note = ""
        bar = wx.BoxSizer(wx.HORIZONTAL)
        self._include_read = wx.CheckBox(panel, label="&Include read notifications")
        self._include_read.SetName("Include notifications you have already read")
        self._include_read.SetHelpText(
            "Checked, the list shows read notifications as well as unread ones. "
            "Changing it loads the inbox again."
        )
        self._done_btn = wx.Button(panel, label="Mark &Done")
        self._done_btn.SetName("Mark the selected notification done")
        self._done_btn.SetHelpText(
            "Takes the notification off your GitHub inbox, as Done does on github.com, "
            "and moves to the next one. Delete in the list does the same."
        )
        self._unsubscribe_btn = wx.Button(panel, label="&Unsubscribe")
        self._unsubscribe_btn.SetName("Unsubscribe from the selected notification's thread")
        self._unsubscribe_btn.SetHelpText(
            "Stops notifications for this thread until you comment or are mentioned, "
            "and takes it out of the list."
        )
        self._read_all_btn = wx.Button(panel, label="Mark &All Read")
        self._read_all_btn.SetName("Mark every notification read")
        self._read_all_btn.SetHelpText(
            "Marks every notification in your GitHub inbox read, up to the moment this "
            "list was loaded. Anything newer stays unread. QUILL asks first."
        )
        bar.Add(self._include_read, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        for button in (self._done_btn, self._unsubscribe_btn, self._read_all_btn):
            bar.Add(button, 0, wx.RIGHT, 6)
        root.Add(bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._notification_bar = bar
        self._include_read.Bind(wx.EVT_CHECKBOX, self._load)
        self._done_btn.Bind(wx.EVT_BUTTON, lambda _event: self._triage_notification(False))
        self._unsubscribe_btn.Bind(wx.EVT_BUTTON, lambda _event: self._triage_notification(True))
        self._read_all_btn.Bind(wx.EVT_BUTTON, lambda _event: self._mark_all_read())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_notification_key)

    def _include_read_value(self) -> bool:
        box = getattr(self, "_include_read", None)
        return bool(box is not None and box.GetValue())

    def _update_notification_controls(self) -> None:
        bar = getattr(self, "_notification_bar", None)
        if bar is None:
            return
        in_view = self._view_key() == "notifications"
        self._notification_root.Show(bar, in_view, recursive=True)
        row = self._selected()
        has_row = in_view and row is not None and row.kind == "notification"
        self._done_btn.Enable(has_row)
        self._unsubscribe_btn.Enable(has_row)
        self._read_all_btn.Enable(in_view and bool(self._rows))
        self._notification_panel.Layout()

    def _notification_poll_blocks(self, token: int, selected_key: str) -> bool:
        """True when GitHub's poll interval says not yet; shows the last list instead."""
        include_read = self._include_read_value()
        wait = self._client.notification_wait_seconds(include_read)
        if wait <= 0:
            self._notification_note = ""
            return False
        self._notification_note = (
            f" GitHub asks apps to check notifications no more often than it says; "
            f"this is the list from the last check. Try again in {wait} seconds."
        )
        rows = self._client.cached_notification_rows(include_read)
        self._loaded(token, GitHubFetchResult(tuple(rows)), "", None, "notifications", selected_key)
        return True

    def _notifications_loaded_message(self) -> str:
        message = self._client.notification_summary(self._include_read_value())
        note, self._notification_note = self._notification_note, ""
        return message + note

    def _on_notification_key(self, event: object) -> None:
        wx = self._wx
        if (
            self._view_key() == "notifications"
            and event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE)
            and not event.HasAnyModifiers()
        ):
            self._triage_notification(False)
            return
        event.Skip()

    def _row_index(self, key: str) -> int:
        return next(
            (
                i
                for i, row in enumerate(self._rows)
                if row.kind == "notification" and row.key == key
            ),
            -1,
        )

    # -- Enter: read it and open it in QUILL ---------------------------------

    def _activate_notification(self, row: ExploreRow) -> None:
        note = self._client.notification(self._include_read_value(), row.key)
        if note is not None and note.unread:
            self._mark_seen(row.key)
        try:
            reference = parse_github_reference(row.url) if row.url else None
        except GitHubReferenceError:
            reference = None
        if reference is not None and reference.kind == "pull_request" and reference.number:
            from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog

            GitHubPullReviewDialog(
                self.dialog,
                self._client._provider,
                reference.repository,
                reference.number,
                announce_cb=self._announce,
            ).show()
            return
        opener = getattr(self, "_on_open_reference", None)
        if reference is not None and reference.kind == "issue" and opener is not None:
            opener(reference)
            self.dialog.EndModal(self._wx.ID_OK)
            return
        self._open(None)

    def _mark_seen(self, key: str) -> None:
        def worker() -> None:
            try:
                self._client.mark_notification_seen(key)
            except GitHubExploreError as exc:
                self._wx.CallAfter(self._seen_failed, str(exc))
                return
            self._wx.CallAfter(self._seen_done, key)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: mark one read.

    def _seen_done(self, key: str) -> None:
        if not dialog_alive(self.dialog) or self._view_key() != "notifications":
            return
        index = self._row_index(key)
        note = self._client.notification(self._include_read_value(), key)
        if index < 0 or note is None:
            return
        self._rows[index] = notification_row(note)
        self._list.SetString(index, self._rows[index].label)

    def _seen_failed(self, message: str) -> None:
        if dialog_alive(self.dialog):
            self._status.SetLabel(f"Could not mark it read: {message}")
            self._announce(f"Could not mark it read: {message}")

    # -- Done, Unsubscribe, Mark All Read --------------------------------------

    def _triage_notification(self, unsubscribe: bool) -> None:
        row = self._selected()
        if row is None or row.kind != "notification" or not row.key:
            self._announce("Select a notification first.")
            return
        key = row.key

        def action() -> str | None:
            if unsubscribe:
                self._client.unsubscribe_notification(key)
            else:
                self._client.mark_notification_done(key)
            return None

        success = "Unsubscribed from the thread." if unsubscribe else "Marked done."
        self._run_notification_write(action, success, lambda: self._remove_notification(key))

    def _remove_notification(self, key: str) -> str:
        index = self._row_index(key)
        if index < 0:
            return ""
        count = len(self._rows)
        del self._rows[index]
        self._list.Delete(index)
        target = selection_after_removal(count, index)
        if target >= 0:
            self._list.SetSelection(target)
            self._select(None)
        else:
            self._select(None)
            self._detail.SetValue("")
        self._list.SetFocus()
        return "" if self._rows else " No notifications left in this list."

    def _mark_all_read(self) -> None:
        if not self._rows:
            self._announce("There are no notifications to mark read.")
            return
        if not self._confirm(
            "Mark every notification in your GitHub inbox read, up to when this list "
            "was loaded? Newer notifications stay unread.",
            "Mark All Read",
        ):
            return

        def action() -> str | None:
            if self._client.mark_all_notifications_read():
                return None
            return (
                "GitHub accepted the request and is marking them read in the background. "
                "Refresh in a minute to check."
            )

        self._run_notification_write(action, "Marked all notifications read.", self._show_all_read)

    def _show_all_read(self) -> str:
        include_read = self._include_read_value()
        rows = self._client.cached_notification_rows(include_read)
        self._rows = list(rows)
        self._list.Set([row.label for row in self._rows])
        if self._rows:
            self._list.SetSelection(0)
        self._select(None)
        return ""

    def _run_notification_write(
        self,
        action: Callable[[], str | None],
        success: str,
        on_success: Callable[[], str],
    ) -> None:
        if self._write_in_flight:
            self._announce("Wait for the current GitHub action to finish before starting another.")
            return
        self._write_in_flight = True
        self._write_token += 1
        token = self._write_token
        self._status.SetLabel("Sending to GitHub...")

        def worker() -> None:
            wx = self._wx
            try:
                override = action()
            except GitHubExploreError as exc:
                wx.CallAfter(self._notification_write_done, token, str(exc), None)
                return
            except Exception as exc:  # noqa: BLE001 - unexpected failures stay visible
                wx.CallAfter(self._notification_write_done, token, f"Action failed: {exc}", None)
                return
            wx.CallAfter(self._notification_write_done, token, override or success, on_success)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: inbox triage.

    def _notification_write_done(
        self, token: int, message: str, on_success: Callable[[], str] | None
    ) -> None:
        if token != self._write_token or not dialog_alive(self.dialog):
            return
        self._write_in_flight = False
        if on_success is not None and self._view_key() == "notifications":
            message += on_success()
        self._status.SetLabel(message)
        self._announce(message)
        self._update_notification_controls()
