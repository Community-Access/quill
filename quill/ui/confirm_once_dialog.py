"""A confirmation that can be told to stop asking.

There were two of these already -- Mark All as Played, and Quill Radio's close
confirm -- and a third was asked for (2026-08-18: *"if delete is pressed offer
a checkbox for do not ask again. this is when pressing delete or selecting
delete from the context menu"*). Three copies of a dialog is where a fourth
starts behaving differently from the other three, so this is the one of them.

Everything a caller supplies is the *question*: the title, the sentence, the
affirmative button's words, and the key the answer is remembered under. The
rules are not negotiable and live here:

**The gate is one call.** :func:`confirm_once` reads the preference, asks only
if it is still wanted, and persists the answer. A caller that had to read the
pref itself is a caller that can forget to.

**The checkbox only counts alongside a Yes.** Cancelling with it ticked must
not silently disable a confirmation that was, in that same gesture, *declined
rather than answered* -- that is how somebody ends up with a destructive verb
that stopped asking without them ever agreeing to it.

**Escape is No.** Always, and it never remembers anything.

The store is :mod:`quill.core.podcasts.ask_prefs`, shared between Quill Radio
and Quill Cast, so an answer given in one app is honoured in the other.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


def confirm_once(
    parent: object,
    *,
    title: str,
    message: str,
    affirmative: str,
    question_key: str,
    announce: Callable[[str], None] | None = None,
    quiet_note: str = "",
) -> bool:
    """Ask *message*, unless the listener has said not to. True means proceed.

    *quiet_note* is what the checkbox's accessible name says this will stop
    asking about -- a checkbox reading only "Don't ask me again" leaves the
    listener to work out *again about what*.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts import ask_prefs

    data_dir = app_data_dir()
    if not ask_prefs.should_ask(data_dir, question_key):
        return True
    confirmed, dont_ask = ConfirmOnceDialog(
        parent,
        title=title,
        message=message,
        affirmative=affirmative,
        announce_cb=announce,
        quiet_note=quiet_note or title,
    ).show()
    if confirmed and dont_ask:
        ask_prefs.set_should_ask(data_dir, question_key, False)
    return confirmed


class ConfirmOnceDialog:
    """Returns ``(confirmed, dont_ask_again)``; Escape/Cancel is ``(False, False)``."""

    def __init__(
        self,
        parent: object,
        *,
        title: str,
        message: str,
        affirmative: str,
        announce_cb: Callable[[str], None] | None = None,
        quiet_note: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._title = title
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(parent, title=title)
        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(self.dialog, label=message)
        intro.Wrap(380)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._dont_ask_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._dont_ask_check.SetName(
            f"Don't ask me again -- {quiet_note or title} happens without this "
            "question from now on, in Quill Radio and Quill Cast alike"
        )
        root.Add(self._dont_ask_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        yes_btn = wx.Button(self.dialog, wx.ID_OK, affirmative)
        yes_btn.SetDefault()
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.Add(yes_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

    def show(self) -> tuple[bool, bool]:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            answer = show_modal_dialog(self.dialog, self._title, announce=self._announce)
            confirmed = answer == wx.ID_OK
            return (confirmed, confirmed and self._dont_ask_check.GetValue())
        finally:
            self.dialog.Destroy()
