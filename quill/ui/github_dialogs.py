"""Dialogs for File > Open Remote > GitHub (File-GH-1 through File-GH-4).

All surfaces use native wxPython controls. Dialogs collect input and return
plain data; side effects (token persistence, file download, tab creation) live
in ``GitHubRemoteMixin`` (``main_frame_github.py``).

Accessibility contract:
- Every interactive control has a ``SetName`` accessible name.
- Errors and progress messages are spoken via the status label (screen readers
  will announce them when focus moves; callers may also use ``_announce``).
- No custom-drawn controls.
- All navigation is keyboard-completable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

if TYPE_CHECKING:
    from collections.abc import Sequence

    from quill.core.github.accounts import GitHubAccount


# ---------------------------------------------------------------------------
# Consent dialog (one-time, shown before any GitHub network access)
# ---------------------------------------------------------------------------

_CONSENT_TEXT = (
    "QUILL can connect to GitHub to browse repositories and open files you choose.\n\n"
    "No content is downloaded until you select a file. You can remove GitHub access "
    "later from File > Open Remote > Manage GitHub Accounts.\n\n"
    "Do you want to continue?"
)


class GitHubConsentDialog:
    """One-time network-access notice. Returns True if the user accepts."""

    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(parent, title="GitHub Access", style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)
        text = wx.StaticText(panel, label=_CONSENT_TEXT)
        text.Wrap(440)
        sizer.Add(text, flag=wx.ALL, border=12)
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Continue")
        ok_btn.SetHelpText("Agree and go on. QUILL then talks to GitHub for you.")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        cancel_button = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_button.SetHelpText("Close without changing anything. Escape does the same.")
        btn_sizer.AddButton(cancel_button)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)
        self.dialog.SetSizerAndFit(wx.BoxSizer(wx.VERTICAL))
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()

    def show(self) -> bool:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            return show_modal_dialog(self.dialog, "GitHub Access") == wx.ID_OK
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Sign-in dialog (token entry or anonymous)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SignInResult:
    """Token or empty string for anonymous."""

    token: str  # "" means anonymous


class GitHubSignInDialog:
    """Add Token, the advanced road: paste a personal access token, or go on anonymously.

    Sign In with GitHub (:mod:`quill.ui.github_device_sign_in`) is the default
    since 2026-11-07; this window is for a token made by hand, such as a
    fine-grained token limited to a few repositories.
    """

    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(parent, title="Add GitHub Token", style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label=(
                "Most people should choose Sign In with GitHub instead. Paste a token here "
                "when you want one you made yourself, such as a fine-grained token limited "
                "to a few repositories, or continue anonymously to browse public "
                "repositories only."
            ),
        )
        intro.Wrap(440)
        sizer.Add(intro, flag=wx.ALL, border=12)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)
        token_label = wx.StaticText(panel, label="Personal access token")
        self._token_ctrl = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._token_ctrl.SetName("Personal access token")
        self._token_ctrl.SetHelpText(
            "A personal access token you made on GitHub. QUILL asks GitHub whose it is "
            "before it keeps it."
        )
        grid.Add(token_label, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._token_ctrl, 1, wx.EXPAND)
        sizer.Add(grid, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        help_text = wx.StaticText(
            panel,
            label=(
                "Create a token at github.com > Settings > Developer settings >\n"
                "Personal access tokens. Select 'repo' scope for private repos."
            ),
        )
        help_text.Wrap(440)
        sizer.Add(help_text, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        self._connect_btn = wx.Button(panel, wx.ID_OK, label="Connect")
        self._connect_btn.SetHelpText("Sign in with the token you typed or the browser sign-in.")
        self._connect_btn.SetDefault()
        btn_sizer.AddButton(self._connect_btn)
        anon_btn = wx.Button(panel, wx.ID_APPLY, label="Continue Anonymously")
        anon_btn.SetHelpText("Go on without signing in. Public repositories can still be read.")
        btn_sizer.AddButton(anon_btn)
        cancel_button = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_button.SetHelpText("Close without changing anything. Escape does the same.")
        btn_sizer.AddButton(cancel_button)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        anon_btn.Bind(wx.EVT_BUTTON, self._on_anonymous)

    def _on_anonymous(self, _event: object) -> None:
        self.dialog.EndModal(self._wx.ID_APPLY)

    def show(self) -> SignInResult | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            result = show_modal_dialog(self.dialog, "Add GitHub Token")
            if result == wx.ID_CANCEL:
                return None
            if result == wx.ID_APPLY:
                return SignInResult(token="")
            token = self._token_ctrl.GetValue().strip()
            if not token:
                return SignInResult(token="")
            return SignInResult(token=token)
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Manage accounts dialog
# ---------------------------------------------------------------------------


class GitHubManageAccountsDialog:
    """Switch, add, or remove locally stored GitHub.com accounts."""

    def __init__(
        self,
        parent: object,
        *,
        login: str | None = None,
        has_token: bool = False,
        accounts: Sequence[GitHubAccount] = (),
        active_account_id: str | None = None,
        status_note: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._accounts = list(accounts)
        self._active_account_id = active_account_id
        self._choice: Any | None = None
        self._switch_id = wx.NewIdRef()
        self._remove_id = wx.NewIdRef()
        self.dialog = wx.Dialog(
            parent, title="Manage GitHub Accounts", style=wx.DEFAULT_DIALOG_STYLE
        )
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        active = next(
            (account for account in self._accounts if account.id == active_account_id), None
        )
        if active is not None:
            status_text = f"Active account: {active.login} on {active.host}"
        elif has_token and login:
            status_text = f"Signed in as: {login}"
        elif has_token:
            status_text = "A saved token could not be verified"
        else:
            status_text = "No GitHub account connected (anonymous access)"

        status = wx.StaticText(panel, label=status_text)
        status.SetName("GitHub account status")
        sizer.Add(status, flag=wx.ALL, border=12)

        if self._accounts:
            account_label = wx.StaticText(panel, label="Saved accounts:")
            sizer.Add(account_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=12)
            labels = [
                f"{account.login} ({account.host})"
                + (" — active" if account.id == active_account_id else "")
                for account in self._accounts
            ]
            self._choice = wx.Choice(panel, choices=labels)
            self._choice.SetHelpText(
                "The GitHub accounts QUILL knows. Choose one to use or remove."
            )
            self._choice.SetName("Saved GitHub accounts")
            selected = next(
                (
                    index
                    for index, account in enumerate(self._accounts)
                    if account.id == active_account_id
                ),
                0,
            )
            self._choice.SetSelection(selected)
            sizer.Add(self._choice, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        if status_note:
            diagnostic = wx.StaticText(panel, label=status_note)
            diagnostic.SetName("GitHub sign-in diagnostic")
            diagnostic.Wrap(480)
            sizer.Add(diagnostic, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        ways = wx.StaticText(
            panel,
            label=(
                "Sign In with GitHub gives you a short code to type on GitHub's page; "
                "nothing to copy out of GitHub's settings. Add Token is for a token you "
                "made yourself, such as a fine-grained one limited to a few repositories."
            ),
        )
        ways.Wrap(480)
        sizer.Add(ways, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        self._sign_in_id = wx.NewIdRef()
        sign_in_btn = wx.Button(panel, int(self._sign_in_id), label="&Sign In with GitHub...")
        sign_in_btn.SetName("Sign in with GitHub")
        sign_in_btn.SetHelpText(
            "Signs in with a short code: QUILL copies it and opens GitHub's page, you "
            "type it there and approve QUILL. The account is added and becomes active."
        )
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(sign_in_btn, flag=wx.RIGHT, border=8)
        self._switch_btn = wx.Button(panel, int(self._switch_id), label="Use Selected Account")
        self._switch_btn.SetHelpText("Make the selected account the one QUILL uses for GitHub.")
        self._switch_btn.SetName("Use selected GitHub account")
        self._switch_btn.Enable(
            self._selected_account_id() is not None
            and self._selected_account_id() != active_account_id
        )
        btn_sizer.Add(self._switch_btn, flag=wx.RIGHT, border=8)
        self._remove_btn = wx.Button(panel, int(self._remove_id), label="Remove Selected Account")
        self._remove_btn.SetHelpText(
            "Forget the selected account on this computer. Its token is removed."
        )
        self._remove_btn.SetName("Remove selected GitHub account")
        self._remove_btn.Enable(bool(self._accounts) or has_token)
        btn_sizer.Add(self._remove_btn, flag=wx.RIGHT, border=8)
        add_btn = wx.Button(panel, wx.ID_ADD, label="Add &Token (Advanced)...")
        add_btn.SetName("Add a GitHub token, advanced")
        add_btn.SetHelpText(
            "Paste a personal access token you made on GitHub, for example a "
            "fine-grained token limited to a few repositories."
        )
        btn_sizer.Add(add_btn)
        sizer.Add(btn_sizer, flag=wx.LEFT | wx.RIGHT, border=12)

        sizer.AddSpacer(8)
        close_btn = wx.Button(panel, wx.ID_OK, label="Done")
        close_btn.SetHelpText("Close Manage GitHub Accounts.")
        # Sign In with GitHub is the default until there is an account to use;
        # after that Enter closes, so a second sign-in is never an accident.
        if active is None and not (has_token and login):
            sign_in_btn.SetDefault()
        else:
            close_btn.SetDefault()
        close_row = wx.BoxSizer(wx.HORIZONTAL)
        close_row.AddStretchSpacer()
        close_row.Add(close_btn)
        sizer.Add(close_row, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        self._switch_btn.Bind(wx.EVT_BUTTON, self._on_switch)
        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        if self._choice is not None:
            self._choice.Bind(wx.EVT_CHOICE, self._on_account_selected)
        add_btn.Bind(wx.EVT_BUTTON, self._on_add)
        sign_in_btn.Bind(wx.EVT_BUTTON, self._on_sign_in)
        self._sign_in_btn = sign_in_btn

    def _selected_account_id(self) -> str | None:
        if self._choice is None or not self._accounts:
            return None
        index = self._choice.GetSelection()
        return self._accounts[index].id if 0 <= index < len(self._accounts) else None

    def _on_account_selected(self, _event: object) -> None:
        selected = self._selected_account_id()
        self._switch_btn.Enable(selected is not None and selected != self._active_account_id)
        self._remove_btn.Enable(selected is not None)

    def _on_switch(self, _event: object) -> None:
        if self._selected_account_id() is not None:
            self.dialog.EndModal(self._switch_id)

    def _on_remove(self, _event: object) -> None:
        self.dialog.EndModal(self._remove_id)

    def _on_add(self, _event: object) -> None:
        self.dialog.EndModal(self._wx.ID_ADD)

    def _on_sign_in(self, _event: object) -> None:
        self.dialog.EndModal(self._sign_in_id)

    def show(self) -> str:
        """``sign_in``, ``switch:<id>``, ``remove:<id>``, ``remove:legacy``, ``add`` or ``done``."""
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        try:
            result = show_modal_dialog(self.dialog, "Manage GitHub Accounts")
            if result == self._switch_id:
                account_id = self._selected_account_id()
                return f"switch:{account_id}" if account_id else "done"
            if result == self._remove_id:
                account_id = self._selected_account_id()
                if account_id:
                    return f"remove:{account_id}"
                return "remove:legacy"
            if result == self._sign_in_id:
                return "sign_in"
            if result == wx.ID_ADD:
                return "add"
            return "done"
        finally:
            self.dialog.Destroy()
