"""Manage GitHub Accounts for ``MainFrame``: check the saved login, then add, switch or remove.

Moved out of :mod:`quill.ui.main_frame_github` on 2026-11-07 (GATE-11). It is a base
of ``GitHubRemoteMixin`` rather than of ``MainFrame`` itself, so the frame's own base
list (and ``main_frame.py``'s size budget) did not change.

Threading: ``_github_fetch_identity_for_manage`` runs on a worker thread and hands the
result to the UI thread with ``CallAfter``; ``_github_show_manage_dialog`` runs on the UI
thread.
"""

from __future__ import annotations

from quill.core.github.accounts import (
    GitHubAccount,
    active_github_account_id,
    list_github_accounts,
    remove_github_account,
    save_github_account,
    set_active_github_account,
)
from quill.core.github.github_provider import GitHubRemoteProvider
from quill.core.github.token_store import delete_legacy_github_token

__all__ = ["GitHubAccountsMixin"]


class GitHubAccountsMixin:
    """The account checks and the Manage GitHub Accounts dialog flow."""

    def _github_fetch_identity_for_manage(
        self,
        token: str,
        accounts: list[GitHubAccount],
        active_id: str | None,
    ) -> None:
        login: str | None = None
        status_note = ""
        try:
            provider = GitHubRemoteProvider(token=token)
            acc = provider.get_identity()
            login = acc.login if acc else None
            status_note = provider.last_auth_error
            provider.close()
        except Exception:  # noqa: BLE001 - never hide the account manager
            status_note = "QUILL could not check the saved GitHub account."

        # Migrate the pre-account token only after GitHub confirms its login.
        # Invalid legacy tokens stay available until the user adds or removes one.
        if login and not accounts:
            try:
                migrated = save_github_account(login, token)
                delete_legacy_github_token()
                accounts = list_github_accounts()
                active_id = migrated.id
                status_note = "Your saved token was added to the account list."
            except Exception:  # noqa: BLE001 - leave the old token usable
                status_note = (
                    "GitHub confirmed the account, but QUILL could not migrate its token. "
                    "Check that the device credential store is available."
                )
        self._wx.CallAfter(
            self._github_show_manage_dialog,
            login=login,
            has_token=True,
            accounts=accounts,
            active_account_id=active_id,
            status_note=status_note,
        )

    def _github_show_manage_dialog(
        self,
        login: str | None,
        has_token: bool,
        accounts: list[GitHubAccount],
        active_account_id: str | None,
        status_note: str,
    ) -> None:
        from quill.ui.github_dialogs import GitHubManageAccountsDialog

        action = GitHubManageAccountsDialog(
            self.frame,
            login=login,
            has_token=has_token,
            accounts=accounts,
            active_account_id=active_account_id,
            status_note=status_note,
        ).show()
        if action.startswith("switch:"):
            account_id = action.removeprefix("switch:")
            if set_active_github_account(account_id):
                account = next((item for item in accounts if item.id == account_id), None)
                label = account.login if account is not None else "GitHub account"
                self._set_status(f"Switched to GitHub account {label}")
        elif action.startswith("remove:"):
            account_id = action.removeprefix("remove:")
            if account_id == "legacy":
                removed = delete_legacy_github_token()
            else:
                removed = remove_github_account(account_id)
            active = next(
                (item for item in list_github_accounts() if item.id == active_github_account_id()),
                None,
            )
            if active is not None:
                self._set_status(f"Removed saved token. Active account: {active.login}")
            elif removed:
                self._set_status("GitHub account disconnected from this QUILL product")
            else:
                self._set_status("No saved GitHub token was removed")
        elif action == "add":
            self._github_add_token()
