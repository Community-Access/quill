"""The warning before Beta or Dev (plan 7.3 and 7.4).

Focus lands on the text, not on a button, so a screen reader starts reading
the reason the window exists. The risk is carried by words and button text,
never by colour or an icon.

**An explicit confirmation is required.** Move does nothing until the "I
understand" box is ticked; pressing it early moves focus to the box and says
why -- an outcome the screen reader cannot know, so saying it is allowed
(GATE-13). Stay on Stable is the default and Escape. Typing a phrase is not
asked for: that costs a braille or speech user far more than it proves.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

import wx

from quill.core.updater.channels import BETA, DEV, channel_label
from quill.core.updater.switch import RiskContext
from quill.core.updater.wording import risk_confirm_label, risk_text, risk_title
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

__all__ = ["RiskAnswer", "RiskDialog", "TICK_FIRST"]

RiskAnswer = Literal["move", "beta_instead", "stay"]

#: Said when Move is pressed before the box is ticked.
TICK_FIRST = "Tick the box first, so we know you've read this."

_BETA_INSTEAD = 5101


class RiskDialog(wx.Dialog):  # type: ignore[misc]
    """Ask before moving to Beta or Dev. :meth:`answer` after the modal returns."""

    def __init__(
        self, parent: Any, context: RiskContext, *, announce: Callable[[str], None]
    ) -> None:
        super().__init__(
            parent,
            title=risk_title(context.display_name, context.target),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._announce = announce
        self._answer: RiskAnswer = "stay"
        label = channel_label(context.target)
        sizer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(self, label="&Before you move:")
        sizer.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self._text = wx.TextCtrl(
            self,
            value=risk_text(context),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 300),
        )
        self._text.SetName("Before you move")
        self._text.SetHelpText(
            f"What {label} means, what could go wrong, how your settings are "
            "protected, and how to come back. Read-only; arrow through it like a document."
        )
        sizer.Add(self._text, 1, wx.EXPAND | wx.ALL, 12)
        self._understood = wx.CheckBox(self, label=risk_confirm_label(context.target))
        self._understood.SetHelpText(
            f"Tick this to say you have read the warning. Move to {label} does "
            "nothing until it is ticked."
        )
        sizer.Add(self._understood, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        if context.target == DEV:
            instead = wx.Button(self, _BETA_INSTEAD, label=f"Choose &{channel_label(BETA)} instead")
            instead.SetHelpText("Close this and look at Beta instead, which is safer than Dev.")
            instead.Bind(wx.EVT_BUTTON, lambda _e: self._finish("beta_instead"))
            buttons.Add(instead, 0, wx.RIGHT, 6)
        move = wx.Button(self, wx.ID_OK, label=f"&Move to {label}")
        move.SetHelpText(
            f"Save a copy of your settings, then move to {label}. Needs the box above ticked."
        )
        move.Bind(wx.EVT_BUTTON, self._on_move)
        buttons.Add(move, 0, wx.RIGHT, 6)
        stay = wx.Button(self, wx.ID_CANCEL, label="Stay on Stable")
        stay.SetHelpText("Close this and change nothing.")
        bind_close_button(self, stay, modeless=False)
        stay.SetDefault()
        buttons.Add(stay, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.SetSizerAndFit(sizer)
        self.SetSize((600, -1))
        apply_modal_ids(self, escape_id=wx.ID_CANCEL)
        self._text.SetFocus()

    def answer(self) -> RiskAnswer:
        return self._answer

    def _on_move(self, _event: object) -> None:
        if not self._understood.GetValue():
            self._understood.SetFocus()
            self._announce(TICK_FIRST)
            return
        self._finish("move")

    def _finish(self, answer: RiskAnswer) -> None:
        self._answer = answer
        self.EndModal(wx.ID_OK if answer == "move" else wx.ID_CANCEL)
