"""Mastodon read/interact commands: view a profile (follow/unfollow + who you
are to each other) and add a user to one of your lists.

Thin wx wiring over :mod:`quill.core.mastodon.social`. Network fetches run on the
task manager; the follow/unfollow toggle runs under a busy cursor from the
profile dialog's button. Disabled in Safe Mode. Host provides ``frame``, ``_wx``,
``_safe_mode``, ``_task_manager``, ``_announce_result``.
"""

from __future__ import annotations

from typing import Any


class MastodonSocialMixin:
    frame: Any
    _wx: Any
    _safe_mode: bool
    _task_manager: Any

    def _announce_result(self, message: str) -> None: ...  # provided by host

    def _mastodon_creds(self) -> tuple[Any, str] | None:
        """The default account and its access token, or None (announcing why)."""
        from quill.core.mastodon import accounts as account_store

        if self._safe_mode:
            self._announce_result("Mastodon is disabled in Safe Mode.")
            return None
        accounts = account_store.list_accounts()
        if not accounts:
            self._announce_result("Add a Mastodon account first.")
            return None
        default_id = account_store.default_account_id()
        account = next((a for a in accounts if a.id == default_id), accounts[0])
        token = account_store.access_token_for(account.id)
        if not token:
            self._announce_result("That Mastodon account has no saved sign-in.")
            return None
        return account, token

    def _ask_handle(self, title: str) -> str:
        wx = self._wx
        with wx.TextEntryDialog(self.frame, "Mastodon handle (e.g. @name@server):", title) as dlg:
            dlg.SetName("Mastodon handle")
            from quill.ui.dialog_contract import apply_modal_ids

            apply_modal_ids(dlg, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
            if dlg.ShowModal() != wx.ID_OK:
                return ""
            return dlg.GetValue().strip()

    def view_mastodon_profile(self) -> None:
        """View a Mastodon account: your relationship both ways, with a
        Follow/Unfollow button."""
        creds = self._mastodon_creds()
        if creds is None:
            return
        account, token = creds
        handle = self._ask_handle("View Mastodon Profile")
        if not handle:
            return
        from quill.core.mastodon import social

        self._announce_result(f"Looking up {handle}...")

        def _work(**_kw: object) -> object:
            try:
                who = social.lookup_account(account.instance_url, token, handle)
                rel = social.relationship(account.instance_url, token, who.id)
                return (who, rel)
            except social.MastodonError as exc:
                return exc

        def _done(_op: str, result: object) -> None:
            self._wx.CallAfter(self._open_profile_dialog, account, token, result)

        self._task_manager.submit("mastodon-profile", _work, on_success=_done, on_failure=None)

    def _open_profile_dialog(self, account: Any, token: str, result: object) -> None:
        from quill.core.mastodon import social
        from quill.ui.mastodon_social_dialogs import MastodonProfileDialog

        if isinstance(result, Exception):
            self._announce_result(f"Could not open the profile: {result}")
            return
        who, rel = result  # type: ignore[misc]

        def _toggle(follow: bool) -> object:
            try:
                with self._wx.BusyCursor():
                    return social.set_following(account.instance_url, token, who.id, follow=follow)
            except social.MastodonError as exc:
                self._announce_result(f"Could not update: {exc}")
                return None

        MastodonProfileDialog(
            self.frame,
            account=who,
            relationship=rel,
            on_toggle_follow=_toggle,
            announce=self._announce_result,
        ).show()

    def mastodon_add_user_to_list(self) -> None:
        """Look up an account and add it to one of your Mastodon lists (Mastodon
        requires that you follow the account first)."""
        creds = self._mastodon_creds()
        if creds is None:
            return
        account, token = creds
        handle = self._ask_handle("Add a User to a Mastodon List")
        if not handle:
            return
        from quill.core.mastodon import social

        self._announce_result(f"Looking up {handle} and your lists...")

        def _work(**_kw: object) -> object:
            try:
                who = social.lookup_account(account.instance_url, token, handle)
                lists = social.get_lists(account.instance_url, token)
                return (who, lists)
            except social.MastodonError as exc:
                return exc

        def _done(_op: str, result: object) -> None:
            self._wx.CallAfter(self._finish_add_to_list, account, token, result)

        self._task_manager.submit("mastodon-add-list", _work, on_success=_done, on_failure=None)

    def _finish_add_to_list(self, account: Any, token: str, result: object) -> None:
        from quill.core.mastodon import social
        from quill.ui.mastodon_social_dialogs import choose_from_list

        if isinstance(result, Exception):
            self._announce_result(f"Could not load your lists: {result}")
            return
        who, lists = result  # type: ignore[misc]
        if not lists:
            self._announce_result("You have no Mastodon lists yet.")
            return
        chosen = choose_from_list(self.frame, lists=lists, announce=self._announce_result)
        if chosen is None:
            return
        try:
            with self._wx.BusyCursor():
                social.add_to_list(account.instance_url, token, chosen.id, [who.id])
        except social.MastodonError as exc:
            self._announce_result(str(exc))
            return
        self._announce_result(f"Added {who.label} to {chosen.title}.")
