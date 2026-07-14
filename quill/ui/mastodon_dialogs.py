"""Accessible dialogs for posting to Mastodon (compose + account management).

Thin wx surfaces over the wx-free ``quill.core.mastodon`` package. Plain stock
controls so screen readers handle them natively; every modal goes through
``dialog_contract`` (``show_modal_dialog`` + ``apply_modal_ids``).

Two surfaces:

* :class:`MastodonComposeDialog` -- edit the text (prefilled from the editor),
  pick which account to post from (by nickname), choose visibility, see a live
  character count, and Post.
* :class:`MastodonAccountsDialog` -- add an account (register QUILL on the
  instance + one-time browser authorization), remove one, or set the default.
"""

from __future__ import annotations

import webbrowser

from quill.core.mastodon import accounts as account_store
from quill.core.mastodon import client
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class MastodonComposeDialog:
    """Compose-and-post dialog. After a Post, ``posted_url`` is set."""

    def __init__(
        self,
        parent: object,
        *,
        initial_text: str,
        accounts: list[account_store.MastodonAccount],
        default_account_id: str | None,
        announce=None,
        spell_review=None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        # Optional callable(text_ctrl) -> None that runs the F7 spelling review
        # over the post text. Provided by MainFrame; None in tests / headless use.
        self._spell_review = spell_review
        self._accounts = accounts
        self.posted_url: str | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Post to Mastodon",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((560, 470))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="Post from &account:"), 0, wx.LEFT | wx.TOP, 12)
        self._account_choice = wx.Choice(self.dialog, choices=[a.display_name for a in accounts])
        self._account_choice.SetName("Post from account")
        if accounts:
            selected = next((i for i, a in enumerate(accounts) if a.id == default_account_id), 0)
            self._account_choice.SetSelection(selected)
        root.Add(self._account_choice, 0, wx.EXPAND | wx.ALL, 12)

        root.Add(wx.StaticText(self.dialog, label="Post &text:"), 0, wx.LEFT, 12)
        self._text = wx.TextCtrl(self.dialog, value=initial_text, style=wx.TE_MULTILINE)
        self._text.SetName("Post text")
        root.Add(self._text, 1, wx.EXPAND | wx.ALL, 12)

        self._count = wx.StaticText(self.dialog, label="")
        root.Add(self._count, 0, wx.LEFT | wx.BOTTOM, 12)

        root.Add(wx.StaticText(self.dialog, label="&Visibility:"), 0, wx.LEFT, 12)
        self._visibility = wx.Choice(
            self.dialog, choices=[label for _, label in client.VISIBILITIES]
        )
        self._visibility.SetName("Visibility")
        self._visibility.SetSelection(0)
        root.Add(self._visibility, 0, wx.EXPAND | wx.ALL, 12)

        buttons = wx.StdDialogButtonSizer()
        post_button = wx.Button(self.dialog, wx.ID_OK, "&Post")
        cancel_button = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.AddButton(post_button)
        buttons.AddButton(cancel_button)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Post",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
            escape_id=wx.ID_CANCEL,
        )
        self._text.Bind(wx.EVT_TEXT, lambda _e: self._update_count())
        post_button.Bind(wx.EVT_BUTTON, self._on_post)
        self._update_count()
        self._text.SetInsertionPointEnd()
        self._text.SetFocus()

    def _update_count(self) -> None:
        used = len(self._text.GetValue())
        remaining = client.DEFAULT_CHARACTER_LIMIT - used
        self._count.SetLabel(f"{used} characters, {remaining} remaining")

    def _selected_account(self) -> account_store.MastodonAccount | None:
        if not self._accounts:
            return None
        index = max(0, self._account_choice.GetSelection())
        return self._accounts[index]

    def _on_post(self, _event: object) -> None:
        text = self._text.GetValue()
        if not text.strip():
            self._announce("Cannot post: the text is empty.")
            self._text.SetFocus()
            return
        account = self._selected_account()
        if account is None:
            self._announce("Add an account first.")
            return
        # Proofread before sending when this account opts in (off by default).
        # The review edits the post text in place; re-read it afterwards.
        if account.spell_check_before_post and self._spell_review is not None:
            self._spell_review(self._text)
            text = self._text.GetValue()
            if not text.strip():
                self._announce("Cannot post: the text is empty.")
                self._text.SetFocus()
                return
        visibility = client.VISIBILITIES[max(0, self._visibility.GetSelection())][0]
        token = account_store.access_token_for(account.id)
        if not token:
            self._announce("That account is not signed in. Remove and re-add it.")
            return
        try:
            with self._wx.BusyCursor():
                self.posted_url = client.post_status(account.instance_url, token, text, visibility)
        except client.MastodonError as error:
            self._announce(f"Could not post: {error}")
            return
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> int:
        return show_modal_dialog(self.dialog, "Post to Mastodon", announce=self._announce)


class MastodonAccountsDialog:
    """Add, remove, and choose the default Mastodon account."""

    def __init__(self, parent: object, *, announce=None) -> None:
        import wx

        self._wx = wx
        self._parent = parent
        self._announce = announce or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent,
            title="Mastodon Accounts",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((520, 360))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self.dialog, label="&Accounts:"), 0, wx.LEFT | wx.TOP, 12)
        self._list = wx.ListBox(self.dialog)
        self._list.SetName("Mastodon accounts")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 12)

        self._spellcheck_check = wx.CheckBox(
            self.dialog, label="Spell-check &posts before sending (selected account)"
        )
        self._spellcheck_check.SetName("Spell-check posts before sending")
        root.Add(self._spellcheck_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        row = wx.BoxSizer(wx.HORIZONTAL)
        add_button = wx.Button(self.dialog, label="&Add Account...")
        self._remove_button = wx.Button(self.dialog, label="&Remove")
        self._default_button = wx.Button(self.dialog, label="Set as &Default")
        for button in (add_button, self._remove_button, self._default_button):
            row.Add(button, 0, wx.RIGHT, 8)
        root.Add(row, 0, wx.LEFT | wx.BOTTOM, 12)

        buttons = wx.StdDialogButtonSizer()
        close_button = wx.Button(self.dialog, wx.ID_OK, "&Close")
        buttons.AddButton(close_button)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Close",
            escape_id=wx.ID_OK,
        )
        add_button.Bind(wx.EVT_BUTTON, lambda _e: self._on_add())
        self._remove_button.Bind(wx.EVT_BUTTON, lambda _e: self._on_remove())
        self._default_button.Bind(wx.EVT_BUTTON, lambda _e: self._on_set_default())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._update_button_states())
        self._spellcheck_check.Bind(wx.EVT_CHECKBOX, lambda _e: self._on_toggle_spellcheck())
        self._refresh()
        self._list.SetFocus()

    def _update_button_states(self) -> None:
        """Enable Remove / Set as Default and sync the spell-check box to selection."""
        account = self._selected_account_obj()
        has_selection = account is not None
        self._remove_button.Enable(has_selection)
        self._default_button.Enable(has_selection)
        # Read the flag fresh from the store so it is always correct regardless of
        # toggles, and never resets the list selection (unlike _refresh).
        self._spellcheck_check.Enable(has_selection)
        self._spellcheck_check.SetValue(bool(account and account.spell_check_before_post))

    def _selected_account_obj(self) -> account_store.MastodonAccount | None:
        account_id = self._selected_id()
        return account_store.get_account(account_id) if account_id else None

    def _on_toggle_spellcheck(self) -> None:
        account_id = self._selected_id()
        if account_id is None:
            return
        enabled = bool(self._spellcheck_check.GetValue())
        account_store.set_spell_check_before_post(account_id, enabled)
        self._announce(
            "Spell-check before posting turned on for this account."
            if enabled
            else "Spell-check before posting turned off for this account."
        )

    def _refresh(self) -> None:
        accounts = account_store.list_accounts()
        default_id = account_store.default_account_id()
        labels = []
        for account in accounts:
            mark = "  (default)" if account.id == default_id else ""
            labels.append(f"{account.display_name}{mark}")
        self._list.Set(labels)
        self._account_ids = [a.id for a in accounts]
        if labels:
            self._list.SetSelection(0)
        self._update_button_states()

    def _selected_id(self) -> str | None:
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._account_ids):
            return None
        return self._account_ids[index]

    def _prompt(self, message: str, caption: str, default: str = "") -> str | None:
        # Stock wx.TextEntryDialog already ships accessible OK/Cancel buttons and
        # native Escape handling, so it needs no apply_modal_ids (the dialog
        # button contract is for custom dialogs).
        wx = self._wx
        entry = wx.TextEntryDialog(self.dialog, message, caption, value=default)
        result = show_modal_dialog(entry, caption, announce=self._announce)
        value = entry.GetValue().strip() if result == wx.ID_OK else None
        entry.Destroy()
        return value

    def _on_add(self) -> None:
        instance = self._prompt(
            "Your Mastodon server (for example mastodon.social):",
            "Add Account: Server",
        )
        if not instance:
            return
        nickname = self._prompt(
            "A friendly name for this account (shown in the account list):",
            "Add Account: Nickname",
        )
        if nickname is None:
            return
        try:
            with self._wx.BusyCursor():
                credentials = client.register_app(instance)
            url = client.authorize_url(instance, credentials.client_id)
            webbrowser.open(url)
        except client.MastodonError as error:
            self._announce(f"Could not connect to that server: {error}")
            return
        self._announce("Authorize QUILL in your browser, then paste the code here.")
        code = self._prompt(
            "Paste the authorization code from your browser:",
            "Add Account: Authorization Code",
        )
        if not code:
            return
        try:
            with self._wx.BusyCursor():
                token = client.exchange_code(instance, credentials, code)
        except client.MastodonError as error:
            self._announce(f"Authorization failed: {error}")
            return
        # The @handle is for display only; fetching it must never discard a
        # validly authorized account. If verify_credentials fails (e.g. an
        # older app registration without read scope), keep the account and
        # fall back to the nickname for its label.
        handle = ""
        try:
            with self._wx.BusyCursor():
                handle = client.verify_credentials(instance, token)
        except client.MastodonError:
            handle = ""
        account_store.add_account(
            nickname=nickname,
            instance_url=client.normalize_instance_url(instance),
            handle=handle,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            access_token=token,
        )
        self._refresh()
        self._announce(f"Added {handle or nickname}.")

    def _on_remove(self) -> None:
        account_id = self._selected_id()
        if account_id is None:
            return
        account = account_store.get_account(account_id)
        wx = self._wx
        confirm = wx.MessageDialog(
            self.dialog,
            f"Remove the account {account.display_name if account else ''}? "
            "This deletes its saved sign-in from this computer.",
            "Remove Account",
            wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT,
        )
        # Stock MessageDialog: native Yes/No + Escape, no apply_modal_ids needed.
        result = show_modal_dialog(confirm, "Remove Account", announce=self._announce)
        confirm.Destroy()
        if result != wx.ID_YES:
            return
        account_store.remove_account(account_id)
        self._refresh()
        self._announce("Account removed.")

    def _on_set_default(self) -> None:
        account_id = self._selected_id()
        if account_id is None:
            return
        account_store.set_default_account(account_id)
        self._refresh()
        self._announce("Default account set.")

    def show(self) -> int:
        return show_modal_dialog(self.dialog, "Mastodon Accounts", announce=self._announce)


__all__ = ["MastodonAccountsDialog", "MastodonComposeDialog"]
