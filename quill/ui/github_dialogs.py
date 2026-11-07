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
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(wx.Button(panel, wx.ID_CANCEL, label="Cancel"))
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
    """Collect a GitHub personal access token or allow anonymous access."""

    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(parent, title="Sign in to GitHub", style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label=(
                "Enter a GitHub personal access token to browse private repositories,\n"
                "or continue anonymously to browse public repositories only."
            ),
        )
        intro.Wrap(440)
        sizer.Add(intro, flag=wx.ALL, border=12)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)
        token_label = wx.StaticText(panel, label="Personal access token")
        self._token_ctrl = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._token_ctrl.SetName("Personal access token")
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
        self._connect_btn.SetDefault()
        btn_sizer.AddButton(self._connect_btn)
        anon_btn = wx.Button(panel, wx.ID_APPLY, label="Continue Anonymously")
        btn_sizer.AddButton(anon_btn)
        btn_sizer.AddButton(wx.Button(panel, wx.ID_CANCEL, label="Cancel"))
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
            result = show_modal_dialog(self.dialog, "Sign in to GitHub")
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

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._switch_btn = wx.Button(panel, int(self._switch_id), label="Use Selected Account")
        self._switch_btn.SetName("Use selected GitHub account")
        self._switch_btn.Enable(
            self._selected_account_id() is not None
            and self._selected_account_id() != active_account_id
        )
        btn_sizer.Add(self._switch_btn, flag=wx.RIGHT, border=8)
        self._remove_btn = wx.Button(panel, int(self._remove_id), label="Remove Selected Account")
        self._remove_btn.SetName("Remove selected GitHub account")
        self._remove_btn.Enable(bool(self._accounts) or has_token)
        btn_sizer.Add(self._remove_btn, flag=wx.RIGHT, border=8)
        add_btn = wx.Button(panel, wx.ID_ADD, label="Add Account...")
        add_btn.SetName("Add GitHub account")
        btn_sizer.Add(add_btn)
        sizer.Add(btn_sizer, flag=wx.LEFT | wx.RIGHT, border=12)

        sizer.AddSpacer(8)
        close_btn = wx.Button(panel, wx.ID_OK, label="Done")
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

    def show(self) -> str:
        """Return ``switch:<id>``, ``remove:<id>``, ``remove:legacy``, ``add``, or ``done``."""
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
            if result == wx.ID_ADD:
                return "add"
            return "done"
        finally:
            self.dialog.Destroy()
