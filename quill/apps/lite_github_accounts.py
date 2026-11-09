"""File > Manage GitHub Accounts in QUILL Lite, and the Workbench's sign-in offer.

Until 2026-11-07 QUILL Lite could use a GitHub account only if QUILL had saved
one: the Workbench read the shared credential store and had no way to add to it.
Somebody with only QUILL Lite installed could never sign in at all. The flow is
QUILL's own (:mod:`quill.ui.github_accounts_flow`, shared by both editors); this
module is QUILL Lite's end of it -- the window, its voice, its message box and a
worker thread.

The token expiry warning's QUILL Lite half is here as well (2026-11-08): the
Workbench's gate hands its token to ``_watch_github_token_expiry``, and the
Notifications entry it leaves opens Manage GitHub Accounts again.

The empty Lite window borrows these handlers too (``ShellMenuMixin`` has this
mixin as a base), so nothing here may reach for a document.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

import wx

from quill.ui.dialog_contract import show_message_box, show_modal_dialog
from quill.ui.github_accounts_flow import GitHubAccountsFlow, GitHubAccountsHost

__all__ = ["GitHubAccountsLiteMixin"]

_WORKBENCH = "GitHub Workbench"

#: What the Workbench says when no account is saved. Plain about both roads: a
#: guest can still read public repositories, and signing in is one window away.
_NOT_SIGNED_IN = (
    "You are not signed in to GitHub. Signed in, the Workbench shows your own "
    "repositories, including private ones, and can comment, label and merge for you. "
    "As a guest it can still read public repositories.\n\n"
    "Choose Manage GitHub Accounts to sign in with GitHub now, or Continue as Guest."
)


def _lite_notice_path(window: object) -> object:
    """QUILL Lite's notifications file, for a window without the dictation mixin."""
    from quill.core.lite.paths import data_dir
    from quill.core.notifications import notifications_path

    folder = getattr(getattr(window, "app", None), "data_dir", None)
    return notifications_path(folder if folder is not None else data_dir())


class GitHubAccountsLiteMixin:
    """``cmd_github_manage_accounts`` and the Workbench's no-account question."""

    def _lite_github_accounts_flow(
        self, on_signed_in: Callable[[], None] | None = None
    ) -> GitHubAccountsFlow:
        def say(message: str) -> None:
            self._announce(message)  # type: ignore[attr-defined]

        def message_box(message: str, caption: str, style: int) -> object:
            return show_message_box(message, caption, style, self)

        def in_background(work: Callable[[], None]) -> None:
            threading.Thread(  # GATE-40-OK: one-shot read-only identity check; abandon-safe
                target=work, daemon=True
            ).start()

        return GitHubAccountsFlow(
            GitHubAccountsHost(
                parent=self,
                set_status=say,
                set_status_quiet=say,
                message_box=message_box,
                run_in_background=in_background,
                call_after=wx.CallAfter,
                app_name="QUILL Lite",
            ),
            on_signed_in=on_signed_in,
        )

    def cmd_github_manage_accounts(self) -> None:
        """File > Manage GitHub Accounts: the same window QUILL opens."""
        self._lite_github_accounts_flow().manage()

    def open_github_accounts_notice(self) -> None:
        """A token-expiry entry in Notifications: Manage GitHub Accounts."""
        self.cmd_github_manage_accounts()

    def _watch_github_token_expiry(self, token: str | None) -> None:
        """At the Workbench's gate: warn once a day about a token that expires soon."""
        from quill.ui.github_token_expiry import ExpiryHost, watch_token_expiry

        path = getattr(self, "_dictation_notification_path", None)
        watch_token_expiry(
            ExpiryHost(
                say=self._announce,  # type: ignore[attr-defined]
                call_after=wx.CallAfter,
                app_name="QUILL Lite",
                notice_path=path() if callable(path) else _lite_notice_path(self),
            ),
            token,
        )

    def _github_workbench_as_guest(self, reopen: Callable[[], None]) -> bool:
        """Ask before opening the Workbench with no account. True to go on as a guest.

        Manage GitHub Accounts is the first choice; once an account is added and
        verified, *reopen* opens the Workbench signed in. Cancel opens nothing.
        """
        dialog = wx.MessageDialog(
            self,  # type: ignore[arg-type]
            _NOT_SIGNED_IN,
            _WORKBENCH,
            wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION,
        )
        dialog.SetYesNoCancelLabels("Manage GitHub &Accounts...", "Continue as &Guest", "Cancel")
        try:
            answer = show_modal_dialog(dialog, _WORKBENCH)
        finally:
            dialog.Destroy()
        if answer == wx.ID_YES:
            self._lite_github_accounts_flow(on_signed_in=reopen).manage()
            return False
        return answer == wx.ID_NO
