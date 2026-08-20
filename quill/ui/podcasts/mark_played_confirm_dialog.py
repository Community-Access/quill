"""Mark All as Played's confirmation, with a way to stop being asked.

The verb is safe-but-sweeping (it can clear hundreds of unheard badges at
once), so it confirms by name and count -- but a listener who marks shows
played all day long has answered the same question enough times, and asked
for the standard way out: a **Don't ask me again** checkbox, remembered in
the shared :mod:`quill.core.podcasts.ask_prefs` store so checking it in
Quill Radio quiets Quill Cast too (same verb, same library, one answer).

The callers decide whether to show this at all (they read the pref first);
this dialog only asks and reports. Same shape as Radio's close-confirm.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


def confirm_mark_all_played(parent: object, *, message: str, announce) -> bool:
    """The whole gate in one call: pref, question, remembered answer.

    True means proceed. Reads the shared ask-pref first (quiet in both apps
    once anyone checked the box), shows the dialog otherwise, and persists
    Don't ask me again only alongside a Yes. Both apps call this so the gate
    can never drift between them.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts import ask_prefs

    data_dir = app_data_dir()
    if not ask_prefs.ask_before_mark_all_played(data_dir):
        return True
    confirmed, dont_ask = MarkPlayedConfirmDialog(
        parent, message=message, announce_cb=announce
    ).show()
    if confirmed and dont_ask:
        ask_prefs.set_ask_before_mark_all_played(data_dir, False)
    return confirmed


class MarkPlayedConfirmDialog:
    """Returns ``(confirmed, dont_ask_again)``; Escape/Cancel is ``(False, False)``."""

    def __init__(
        self,
        parent: object,
        *,
        message: str,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._confirmed = False

        self.dialog = wx.Dialog(parent, title="Mark All as Played")
        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(self.dialog, label=message)
        intro.Wrap(380)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._dont_ask_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._dont_ask_check.SetName(
            "Don't ask me again -- future Mark All as Played runs without this question, "
            "in Quill Radio and Quill Cast alike"
        )
        root.Add(self._dont_ask_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        mark_btn = wx.Button(self.dialog, wx.ID_OK, "Mark &Played")
        mark_btn.SetDefault()
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.Add(mark_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

    def show(self) -> tuple[bool, bool]:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            answer = show_modal_dialog(self.dialog, "Mark All as Played", announce=self._announce)
            confirmed = answer == wx.ID_OK
            # The checkbox only counts alongside a Yes: cancelling with it
            # ticked must not silently disable a confirmation that was, in
            # that same gesture, declined rather than answered.
            return (confirmed, confirmed and self._dont_ask_check.GetValue())
        finally:
            self.dialog.Destroy()
