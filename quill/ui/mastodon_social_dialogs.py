"""Read/interact Mastodon dialogs: the profile view (follow/unfollow + who you
are to each other + who favourited a post) and the add-to-list picker.

Thin wx over the wx-free :mod:`quill.core.mastodon.social`. Stock accessible
controls; every modal goes through ``dialog_contract`` (``show_modal_dialog`` +
``apply_modal_ids``). The dialogs never touch the network themselves -- the host
fetches on the task manager and hands in the results.
"""

from __future__ import annotations

from typing import Any

from quill.core.mastodon.social import Account, MastodonList, Relationship
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog


class MastodonProfileDialog:
    """Show one account: its name, your relationship both ways, a Follow/Unfollow
    button, and (optionally) the accounts who favourited or boosted a post.

    ``on_toggle_follow(follow: bool) -> Relationship | None`` performs the
    follow/unfollow (the host runs it, refreshes the relationship, and returns
    the new one, or None on failure); the dialog updates its label and button.
    """

    def __init__(
        self,
        parent: object,
        *,
        account: Account,
        relationship: Relationship,
        on_toggle_follow: Any,
        favouriters: list[Account] | None = None,
        boosters: list[Account] | None = None,
        announce: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._account = account
        self._relationship = relationship
        self._on_toggle_follow = on_toggle_follow
        self._announce = announce or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent,
            title=f"Profile: {account.label}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((520, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        name = wx.StaticText(self.dialog, label=account.label)
        set_accessible_name(name, f"Account: {account.label}")
        root.Add(name, 0, wx.ALL, 12)

        self._relationship_text = wx.StaticText(self.dialog, label=relationship.summary())
        set_accessible_name(self._relationship_text, "Your relationship")
        root.Add(self._relationship_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self._follow_btn = wx.Button(self.dialog, label=self._follow_label())
        set_accessible_name(self._follow_btn, self._follow_label())
        self._follow_btn.Bind(wx.EVT_BUTTON, self._on_follow)
        root.Add(self._follow_btn, 0, wx.LEFT | wx.BOTTOM, 12)

        for heading, people in (("Favourited by", favouriters), ("Boosted by", boosters)):
            if not people:
                continue
            root.Add(wx.StaticText(self.dialog, label=f"&{heading}:"), 0, wx.LEFT, 12)
            listbox = wx.ListBox(self.dialog, choices=[p.label for p in people])
            set_accessible_name(listbox, f"{heading} {len(people)} accounts")
            root.Add(listbox, 1, wx.EXPAND | wx.ALL, 12)

        buttons = wx.StdDialogButtonSizer()
        close_button = wx.Button(self.dialog, wx.ID_CANCEL, "&Close")
        buttons.AddButton(close_button)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        self._follow_btn.SetFocus()

    def _follow_label(self) -> str:
        return "Un&follow" if self._relationship.following else "&Follow"

    def _on_follow(self, _event: object) -> None:
        want_follow = not self._relationship.following
        result = self._on_toggle_follow(want_follow)
        if result is None:
            return  # the host announced the failure
        self._relationship = result
        self._relationship_text.SetLabel(result.summary())
        self._follow_btn.SetLabel(self._follow_label())
        set_accessible_name(self._follow_btn, self._follow_label())
        self._announce(
            f"Now following {self._account.label}."
            if result.following
            else f"No longer following {self._account.label}."
        )

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        try:
            show_modal_dialog(self.dialog, "Mastodon Profile", announce=self._announce)
        finally:
            self.dialog.Destroy()


def choose_from_list(
    parent: object, *, lists: list[MastodonList], announce: Any = None
) -> MastodonList | None:
    """A stock single-choice picker over the user's Mastodon lists. Returns the
    chosen list or None if cancelled / there are none."""
    import wx

    if not lists:
        return None
    dialog = wx.SingleChoiceDialog(
        parent, "Add to which list?", "Mastodon Lists", [mlist.title for mlist in lists]
    )
    try:
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        if show_modal_dialog(dialog, "Mastodon Lists", announce=announce) != wx.ID_OK:
            return None
        return lists[dialog.GetSelection()]
    finally:
        dialog.Destroy()


def choose_account(
    parent: object, *, accounts: list[Account], prompt: str, announce: Any = None
) -> Account | None:
    """A stock single-choice picker over accounts (e.g. the users found in a
    post). Returns the chosen account or None."""
    import wx

    if not accounts:
        return None
    dialog = wx.SingleChoiceDialog(parent, prompt, "Choose an account", [a.label for a in accounts])
    try:
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        if show_modal_dialog(dialog, "Choose an account", announce=announce) != wx.ID_OK:
            return None
        return accounts[dialog.GetSelection()]
    finally:
        dialog.Destroy()
