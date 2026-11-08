"""Manage GitHub Accounts, once, for both editors: check, add, switch, remove.

QUILL reached this flow from File > Open Remote and QUILL Lite could not reach
it at all: Lite's GitHub Workbench used an account QUILL had saved and had no
way to add one of its own. A second copy in ``quill/apps`` would have been the
easy fix and the wrong one (the family rule that QUILL Lite may never be ahead
of QUILL, nor quietly different from it), so the flow moved here out of
``main_frame_github.py`` and ``main_frame_github_accounts.py`` and both editors
drive it.

It is wx-light: it opens the shared dialogs in :mod:`quill.ui.github_dialogs`
and nothing else of wx. Everything that belongs to the window -- the parent,
how a sentence reaches the user, how a message box is shown, how work goes to a
worker thread and back -- is handed in as a :class:`GitHubAccountsHost`.

Threading: the identity checks run through ``run_in_background`` (off the UI
thread) and hand their result back with ``call_after``; every dialog opens on
the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.github.accounts import (
    GitHubAccount,
    active_github_account_id,
    list_github_accounts,
    remove_github_account,
    save_github_account,
    set_active_github_account,
)
from quill.core.github.github_provider import GitHubRemoteProvider
from quill.core.github.token_store import delete_legacy_github_token, load_github_token
from quill.core.platform_nouns import credential_store_name

__all__ = ["GitHubAccountsFlow", "GitHubAccountsHost"]


@dataclass(slots=True)
class GitHubAccountsHost:
    """What the flow needs from the window that runs it."""

    #: The window the dialogs open over.
    parent: Any
    #: An outcome the user should hear ("Switched to GitHub account octocat").
    set_status: Callable[[str], None]
    #: Progress that need not be spoken ("Checking the GitHub account...").
    set_status_quiet: Callable[[str], None]
    #: ``(message, caption, style)``: a message box over *parent*.
    message_box: Callable[[str, str, int], object]
    #: Run a callable off the UI thread.
    run_in_background: Callable[[Callable[[], None]], None]
    #: Run ``fn(*args, **kwargs)`` on the UI thread (``wx.CallAfter``).
    call_after: Callable[..., None]


class GitHubAccountsFlow:
    """The Manage GitHub Accounts flow over one :class:`GitHubAccountsHost`.

    *on_signed_in* is called on the UI thread once a newly added token has been
    verified and saved. QUILL Lite's Workbench uses it to open straight after
    signing in; QUILL passes nothing.
    """

    def __init__(
        self,
        host: GitHubAccountsHost,
        *,
        on_signed_in: Callable[[], None] | None = None,
    ) -> None:
        self.host = host
        self.on_signed_in = on_signed_in

    # -- entry point ------------------------------------------------------ #

    def manage(self) -> None:
        """Open Manage GitHub Accounts, checking any saved token first."""
        token = load_github_token()
        accounts = list_github_accounts()
        active_id = active_github_account_id()
        if token:
            self.host.run_in_background(
                lambda: self.fetch_identity_for_manage(token, accounts, active_id)
            )
            return
        self.show_manage_dialog(
            login=None,
            has_token=False,
            accounts=accounts,
            active_account_id=active_id,
            status_note="",
        )

    # -- the saved account ------------------------------------------------ #

    def fetch_identity_for_manage(
        self,
        token: str,
        accounts: list[GitHubAccount],
        active_id: str | None,
    ) -> None:
        """Worker thread: ask GitHub whose token this is, then show the dialog."""
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
        self.host.call_after(
            self.show_manage_dialog,
            login=login,
            has_token=True,
            accounts=accounts,
            active_account_id=active_id,
            status_note=status_note,
        )

    def show_manage_dialog(
        self,
        login: str | None,
        has_token: bool,
        accounts: list[GitHubAccount],
        active_account_id: str | None,
        status_note: str,
    ) -> None:
        """UI thread: the dialog, then whatever the user chose in it."""
        from quill.ui.github_dialogs import GitHubManageAccountsDialog

        action = (
            GitHubManageAccountsDialog(
                self.host.parent,
                login=login,
                has_token=has_token,
                accounts=accounts,
                active_account_id=active_account_id,
                status_note=status_note,
            ).show()
            or "done"
        )
        set_status = self.host.set_status
        if action.startswith("switch:"):
            account_id = action.removeprefix("switch:")
            if set_active_github_account(account_id):
                account = next((item for item in accounts if item.id == account_id), None)
                label = account.login if account is not None else "GitHub account"
                set_status(f"Switched to GitHub account {label}")
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
                set_status(f"Removed saved token. Active account: {active.login}")
            elif removed:
                set_status("GitHub account disconnected from this QUILL product")
            else:
                set_status("No saved GitHub token was removed")
        elif action == "add":
            self.add_token()

    # -- adding a token --------------------------------------------------- #

    def add_token(self) -> None:
        """UI thread: ask for a token, then verify it off the UI thread."""
        from quill.ui.github_dialogs import GitHubSignInDialog

        result = GitHubSignInDialog(self.host.parent).show()
        if result is None or not result.token:
            return
        token = result.token
        self.host.set_status_quiet("Checking the GitHub account...")
        self.host.run_in_background(lambda: self.verify_new_token(token))

    def verify_new_token(self, token: str) -> None:
        """Worker thread: one read-only identity check, then back to the UI thread."""
        login: str | None = None
        error = ""
        try:
            provider = GitHubRemoteProvider(token=token)
            identity = provider.get_identity()
            login = identity.login if identity else None
            error = provider.last_auth_error
            provider.close()
        except Exception:  # noqa: BLE001 - report without retaining an unverified token
            error = "QUILL could not verify that token with GitHub."
        self.host.call_after(self.add_token_done, token, login, error)

    def add_token_done(self, token: str, login: str | None, error: str) -> None:
        """UI thread: save a verified token, or say why nothing was saved."""
        import wx

        warning = wx.ICON_WARNING | wx.OK
        if not login:
            self.host.message_box(
                error or "GitHub did not confirm an account for that token. Nothing was saved.",
                "GitHub Sign In",
                warning,
            )
            return
        try:
            account = save_github_account(login, token)
            delete_legacy_github_token()
        except Exception:  # noqa: BLE001 - credential-store errors must be clear
            self.host.message_box(
                f"Could not save the verified token. The {credential_store_name()} "
                "may not be available.",
                "GitHub Sign In",
                warning,
            )
            return
        self.host.set_status(f"Added and switched to GitHub account {account.login}")
        if self.on_signed_in is not None:
            self.on_signed_in()
