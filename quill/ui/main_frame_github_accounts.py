"""Manage GitHub Accounts for ``MainFrame``: QUILL's end of the shared flow.

The flow itself -- check the saved login, then add, switch or remove -- lives in
:mod:`quill.ui.github_accounts_flow` since 2026-11-07, where QUILL Lite reaches the
same code. What stays here is the frame's half: the parent window, the status bar,
the message box and the worker thread, handed to the flow as a host.

It is a base of ``GitHubRemoteMixin`` rather than of ``MainFrame`` itself, so the
frame's own base list (and ``main_frame.py``'s size budget) did not change. The
``_github_*`` names are kept because other mixins call them
(``main_frame_github_admin`` offers to sign in through ``_github_sign_in``).

Sign In with GitHub waits for GitHub on the frame's task manager, so the
fifteen-minute wait for a device code is a tracked task, never the UI thread.

The token expiry warning's frame half is here too (2026-11-08): the Workbench's
openers hand their token to :meth:`GitHubAccountsMixin._watch_github_token_expiry`,
and the Notifications entry it leaves opens this window again
(:meth:`GitHubAccountsMixin.open_github_accounts_notice`).
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from quill.ui.github_accounts_flow import GitHubAccountsFlow, GitHubAccountsHost

__all__ = ["GitHubAccountsMixin"]


class GitHubAccountsMixin:
    """The frame's adapter onto :class:`~quill.ui.github_accounts_flow.GitHubAccountsFlow`."""

    def _github_accounts_flow(self) -> GitHubAccountsFlow:
        def in_background(work: Callable[[], None]) -> None:
            threading.Thread(  # GATE-40-OK: one-shot read-only identity check; abandon-safe
                target=work, daemon=True
            ).start()

        return GitHubAccountsFlow(
            GitHubAccountsHost(
                parent=self.frame,
                set_status=self._set_status,
                set_status_quiet=self._set_status_quiet,
                message_box=self._show_message_box,
                run_in_background=in_background,
                call_after=self._wx.CallAfter,
                app_name="QUILL",
                submit=getattr(getattr(self, "_task_manager", None), "submit", None),
            )
        )

    def manage_github_accounts(self) -> None:
        """File > Open Remote > Manage GitHub Accounts..."""
        self._github_accounts_flow().manage()

    def _github_add_token(self) -> None:
        self._github_accounts_flow().add_token()

    def _github_sign_in(self) -> None:
        self._github_accounts_flow().sign_in()

    def open_github_accounts_notice(self) -> None:
        """A token-expiry entry in Notifications: Manage GitHub Accounts."""
        self.manage_github_accounts()

    def _watch_github_token_expiry(self, token: str | None) -> None:
        """At the Workbench's gate: warn once a day about a token that expires soon."""
        from quill.ui.github_token_expiry import ExpiryHost, watch_token_expiry

        def after_notice() -> None:
            # The Notifications cell appears once there is something in it.
            from quill.core.notifications import load_notifications

            self._notifications = load_notifications()
            refresh = getattr(self, "_refresh_statusbar", None)
            if callable(refresh):
                refresh()

        watch_token_expiry(
            ExpiryHost(
                say=self._announce,
                call_after=self._wx.CallAfter,
                app_name="QUILL",
                after_notice=after_notice,
            ),
            token,
        )
