"""One small modal for private-feed credentials, shared by the Add Podcast
401 retry prompt and the show context menu's Feed Credentials... item.

Never touches the credential store itself -- it returns what the user typed
and the caller decides what to persist (add_podcast_dialog retries the fetch
first; show_actions saves/clears). The password never leaves this dialog in
any log or announcement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.ui.dialog_contract import apply_modal_ids


@dataclass(slots=True)
class FeedCredentialsResult:
    """What the user chose: action is ``"save"`` or ``"clear"``. On save, an
    empty password means "keep whatever password is already stored"."""

    action: str
    username: str
    password: str


class FeedCredentialsDialog:
    """Username + masked password, OK/Cancel, optional Clear Credentials."""

    def __init__(
        self,
        parent: object,
        *,
        username: str = "",
        message: str = "",
        allow_clear: bool = False,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: FeedCredentialsResult | None = None

        self.dialog = wx.Dialog(parent, title="Feed Credentials")
        root = wx.BoxSizer(wx.VERTICAL)

        intro = message or (
            "This feed requires a sign-in. Enter the username and password "
            "your podcast provider gave you."
        )
        intro_text = wx.StaticText(self.dialog, label=intro)
        intro_text.Wrap(420)
        root.Add(intro_text, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self.dialog, label="&Username:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._username_ctrl = wx.TextCtrl(self.dialog, value=username, size=(280, -1))
        self._username_ctrl.SetName("The username this feed requires")
        grid.Add(self._username_ctrl, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self.dialog, label="&Password:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._password_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PASSWORD, size=(280, -1))
        self._password_ctrl.SetName("The password this feed requires")
        grid.Add(self._password_ctrl, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        if username:
            keep_note = wx.StaticText(
                self.dialog,
                label="Leave the password blank to keep the stored one.",
            )
            root.Add(keep_note, 0, wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        if allow_clear:
            clear_btn = wx.Button(self.dialog, label="C&lear Credentials")
            clear_btn.SetName("Remove the stored username and password for this feed")
            clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
            btn_row.Add(clear_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "OK")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizerAndFit(root)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        self._username_ctrl.SetFocus()

    def _on_ok(self, _event: object) -> None:
        username = self._username_ctrl.GetValue().strip()
        if not username:
            self._announce("Enter a username first")
            self._username_ctrl.SetFocus()
            return
        self._result = FeedCredentialsResult(
            action="save",
            username=username,
            password=self._password_ctrl.GetValue(),
        )
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_clear(self, _event: object) -> None:
        self._result = FeedCredentialsResult(action="clear", username="", password="")
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> FeedCredentialsResult | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Feed Credentials", announce=self._announce)
            return self._result
        finally:
            self.dialog.Destroy()
