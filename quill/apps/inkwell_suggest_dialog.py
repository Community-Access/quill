"""Suggest Abbreviations: review what the AI proposed, and add only what you check.

codex.md 6.12 and 10E.10. Every proposal is one check box, "abbreviation,
expands to ...", and **every box starts cleared**: an abbreviation is added
only because somebody checked it. Individual check boxes rather than a check
list, because a check list does not say whether a row is checked as you arrow
through it (A11Y-SR-1); each check box says its own state when it gets focus.

OK adds the checked ones (the caller saves them through the library's own save
path); Cancel, Escape and closing add nothing.
"""

from __future__ import annotations

import wx

from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.dpi import dip, dip_size

__all__ = ["SUGGEST_TITLE", "SuggestionsDialog", "proposal_label"]

SUGGEST_TITLE = "Suggest Abbreviations"


def proposal_label(abbreviation: str, expansion: str, *, limit: int = 120) -> str:
    """One proposal as its check box says it, on one line."""
    shown = " ".join(expansion.split())
    if len(shown) > limit:
        shown = shown[: limit - 3].rstrip() + "..."
    # A literal ampersand, never an access key.
    return f"{abbreviation}, expands to {shown}".replace("&", "&&")


class SuggestionsDialog(wx.Dialog):
    """One cleared check box per proposal; OK adds the checked ones."""

    def __init__(self, parent: wx.Window | None, proposals: list[tuple[str, str]]) -> None:
        super().__init__(
            parent,
            title="Suggest Abbreviations",
            size=dip_size(parent, 560, 420),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._proposals = list(proposals)
        root = wx.BoxSizer(wx.VERTICAL)

        count = len(self._proposals)
        noun = "abbreviation" if count == 1 else "abbreviations"
        intro = wx.StaticText(
            self,
            label=(
                f"The AI suggested {count} {noun}. Check the ones to add; "
                "nothing is added unless you check it."
            ),
        )
        root.Add(intro, 0, wx.ALL, dip(self, 10))

        scroller = wx.ScrolledWindow(self, style=wx.VSCROLL | wx.TAB_TRAVERSAL)
        scroller.SetScrollRate(0, dip(self, 12))
        scroller.SetName("Suggested abbreviations")
        rows = wx.BoxSizer(wx.VERTICAL)
        self._boxes: list[wx.CheckBox] = []
        for abbreviation, expansion in self._proposals:
            box = wx.CheckBox(scroller, label=proposal_label(abbreviation, expansion))
            box.SetHelpText(
                "Check this to add the abbreviation to your library when you press OK. "
                "It starts cleared, so nothing the AI suggested is added unless you "
                "check it. You can change or delete it later in Manage Abbreviations."
            )
            box.SetValue(False)
            rows.Add(box, 0, wx.ALL, dip(self, 4))
            self._boxes.append(box)
        scroller.SetSizer(rows)
        root.Add(scroller, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, dip(self, 10))

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, label="OK")
        ok.SetHelpText(
            "Add the abbreviations you checked to your library, the same library "
            "QUILL expands from, and close. If none are checked, nothing is added."
        )
        cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Close without adding any of the suggested abbreviations.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, dip(self, 10))

        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        bind_close_button(self, cancel, modeless=False)
        ok.SetDefault()
        self.SetSizer(root)
        if self._boxes:
            self._boxes[0].SetFocus()

    def checked(self) -> list[tuple[str, str]]:
        """The proposals whose boxes are checked, in the order shown."""
        return [
            proposal
            for proposal, box in zip(self._proposals, self._boxes, strict=True)
            if box.GetValue()
        ]
