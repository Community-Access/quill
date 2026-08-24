"""One setting, one control, focus already on it (list.md 5.7).

The whole point is what is *missing*: no tabs, no groups, no other controls to
arrow past. Somebody who chose "Episodes to Keep" from a context menu has
already said which setting they want, and a window that then asks them to find
it again has spent their keystrokes on navigation they had finished.

Three rules, all of which are the reason this exists rather than a link into
the full settings dialog:

* **Focus lands on the control**, not on OK and not on the first static text.
* **The value shown is the one in force**, inherited default included -- an
  editor that opens on a blank misreports the setting it exists to change.
* **The change is said back in words**, not as a number: "Keeping the 5 newest
  downloaded episodes" is an answer; "5" is a reading of the box that was just
  typed into.

A11Y-4 hardened: modal ids, an escape route, and a Close/Cancel button that
answers.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.single_settings import SingleSetting
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

__all__ = ["SingleSettingDialog"]


class SingleSettingDialog:
    """Edit one number. Returns the new value, or ``None`` when cancelled."""

    def __init__(
        self,
        parent: object,
        setting: SingleSetting,
        *,
        value: float,
        minimum: float = 0.0,
        maximum: float = 999.0,
        decimals: int = 0,
        subject: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._setting = setting
        self._decimals = decimals
        self._minimum = minimum
        self._maximum = maximum
        self._announce = announce_cb or (lambda _m: None)
        self._result: float | None = None

        title = f"{setting.title} -- {subject}" if subject else setting.title
        self._title = title
        self.dialog = wx.Dialog(parent, title=title)
        root = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self.dialog, label=setting.field_label)
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        if decimals:
            self._ctrl = wx.SpinCtrlDouble(
                self.dialog,
                min=minimum,
                max=maximum,
                initial=float(value),
                inc=0.05,
            )
            self._ctrl.SetDigits(decimals)
        else:
            self._ctrl = wx.SpinCtrl(
                self.dialog,
                min=int(minimum),
                max=int(maximum),
                initial=int(value),
            )
        # The name a screen reader speaks on focus, and the F1 answer. Both,
        # because the help is the part that says what zero means, and zero is
        # the value people get wrong.
        self._ctrl.SetName(setting.field_label.replace("&", ""))
        self._ctrl.SetHelpText(setting.help)
        root.Add(self._ctrl, 0, wx.EXPAND | wx.ALL, 10)

        explain = wx.StaticText(self.dialog, label=setting.help)
        explain.Wrap(380)
        root.Add(explain, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&Save")
        ok_btn.SetHelpText("Applies this setting to this podcast only.")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Leaves the setting as it was.")
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )

    def show(self) -> float | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        # The whole feature, in one line: the control, not the button, not the
        # label. CallAfter because wxMSW settles focus after the dialog shows.
        wx.CallAfter(self._ctrl.SetFocus)
        try:
            if show_modal_dialog(self.dialog, self._title, announce=self._announce) != wx.ID_OK:
                return None
            value = float(self._ctrl.GetValue())
            self._result = max(self._minimum, min(self._maximum, value))
            return self._result
        finally:
            self.dialog.Destroy()

    def close(self) -> None:
        self.dialog.EndModal(self._wx.ID_CANCEL)
