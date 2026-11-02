"""ChatGPT Plan Options: web search and Forget, reached from Choose Your AI.

Use My ChatGPT Subscription (Alt+F5) used to open the plan's own account window,
which held two things Choose Your AI's five controls do not: whether the model
may search the web through OpenAI, and **Forget on This Computer** -- the way out
for a computer that is offline, or a sign-in already removed in ChatGPT's
settings. When Alt+F5 began opening Choose Your AI (codex.md 10A.9) both became
unreachable. They live here now, one small step opened by the window's **Plan
Options** button, which is shown only while the ChatGPT plan's row (or Codex's,
which runs on the same sign-in) is selected and signed in -- so the window keeps
its five controls everywhere else (10A.3).

**What is spoken (GATE-13).** Nothing when the check box changes: the reader
says its new state. Forget is an outcome only the app knows, so the window that
opened this says it, through the announcement service (GATE-BRAILLE).
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.hosted_ai_dialogs import _PAD, _read_only

__all__ = ["FORGOTTEN", "TITLE", "PlanOptionsDialog", "show_plan_options"]

TITLE = "ChatGPT Plan Options"
#: What the dialog's caller returns when Forget was pressed.
FORGOTTEN = wx.ID_DELETE


class PlanOptionsDialog(wx.Dialog):
    """Allow web search, Forget on This Computer, and Close."""

    def __init__(self, parent: Any, account: Any, agent: str) -> None:
        super().__init__(parent, title=TITLE)
        self._account = account
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        _read_only(
            self,
            sizer,
            "About these options",
            f"{agent} is signed in to your ChatGPT plan. These choices are saved at once.",
            "What these options are for: the ChatGPT plan this app is signed in to.",
            grow=False,
        )
        self.web = wx.CheckBox(self, label="Allow &web search")
        self.web.SetValue(bool(getattr(account, "web_search", False)))
        self.web.SetHelpText(
            "When checked, the model may search the web through OpenAI to answer a "
            "question. Not checked, only what you send is used. Saved as soon as you "
            "change it."
        )
        self.web.Bind(wx.EVT_CHECKBOX, lambda _e: account.set_web_search(self.web.GetValue()))
        sizer.Add(self.web, 0, wx.ALL, _PAD)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        forget = wx.Button(self, label="&Forget on This Computer")
        forget.SetHelpText(
            "Forgets the sign-in here without telling OpenAI, for a computer that is "
            f"offline or a sign-in you already removed in ChatGPT's settings. {agent} "
            "stays listed there until you remove it."
        )
        forget.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(FORGOTTEN))
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Closes these options. Every choice is already saved.")
        row.Add(forget, 0, wx.RIGHT, _PAD)
        row.Add(close, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetInitialSize(dip_size(self, 480, 220))
        self.Centre()
        self.web.SetFocus()


def show_plan_options(parent: Any, account: Any, agent: str) -> bool:
    """Show the options. True when the person chose Forget (already done here)."""
    dialog = PlanOptionsDialog(parent, account, agent)
    try:
        forgot = show_modal_dialog(dialog, TITLE) == FORGOTTEN
    finally:
        dialog.Destroy()
    if forgot:
        account.forget()
    return forgot
