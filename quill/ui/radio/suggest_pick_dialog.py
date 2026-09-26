"""Community > Suggest a Station or Podcast...: no account, no GitHub.

A suggestion is **an email to support@community-access.org** (2026-09-26). You
fill in the form here; your own mail program opens with the suggestion already
written; you press Send there. A person at Community Access reads it, and
answers if you gave an address.

It used to be a GitHub issue, posted with a token bundled into the build, with
a pre-filled issue page in the browser as the fallback. Both are gone: every
piece of feedback from Quill Radio now goes to one support address, nothing is
filed on a public site, and the app no longer carries a GitHub credential. The
handoff is Get Help from Support's own (``support_dialog.send_by_mail``), so
the length cut, the clipboard copy and the "no mail program" answer are the
same code, not a second copy of it.

Validation happens before anything is written, because catching a duplicate
here costs one dialog and catching it after it reaches a person costs a round
trip through that person.
"""

from __future__ import annotations

from typing import Any

from quill.core.pick_suggestion import (
    Suggestion,
    known_urls,
    support_message,
    validate,
)
from quill.core.support_message import SUPPORT_EMAIL
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.support_dialog import send_by_mail

TITLE = "Suggest a Station or Podcast"

_KINDS = (("A radio station", "stream"), ("A podcast", "podcast"))

#: Said when the mail program opens. Plain about what happened and what is
#: left to do, because the suggestion has not been sent yet.
OPENED = "Your mail program has opened with your suggestion written. Press Send there."


def open_suggest_dialog(host: Any) -> None:
    """Collect a suggestion and hand it to the mail program. Never raises."""
    if getattr(host, "_safe_mode", False):
        host._announce("Safe Mode is on, so nothing is sent anywhere.")
        return
    import wx

    _SuggestDialog(host, wx).show()


class _SuggestDialog:
    def __init__(self, host: Any, wx: Any) -> None:
        self._host = host
        self._wx = wx

    def show(self) -> None:
        wx = self._wx
        self.dialog = wx.Dialog(self._host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Tell us about a station or podcast worth adding to the "
                    f"Community Picks list. It goes to {SUPPORT_EMAIL}: your own "
                    "mail program opens with it written, and nothing is sent "
                    "until you press Send there."
                ),
            ),
            0,
            wx.ALL,
            8,
        )

        grid = wx.FlexGridSizer(0, 2, 6, 8)
        grid.AddGrowableCol(1, 1)
        self._kind = self._choice(
            grid,
            "&What is it:",
            [label for label, _ in _KINDS],
            "Whether this is a live radio station or a podcast feed.",
        )
        self._title_ctrl = self._field(grid, "&Name:", "What it should be called in the list.")
        self._url = self._field(
            grid,
            "&Address:",
            "The stream address for a station, or the feed address for a podcast. "
            "It must start with https.",
        )
        self._description = self._field(
            grid,
            "&Description:",
            "One or two sentences saying what it is, for somebody who has never heard it.",
            multiline=True,
        )
        self._language = self._field(grid, "&Language:", "Such as en, or en-US. Optional.")
        self._why = self._field(
            grid,
            "W&hy it belongs:",
            "Anything that would help decide. Optional; only the people at "
            "Community Access who read the suggestion see it.",
            multiline=True,
        )
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._send = wx.Button(self.dialog, wx.ID_OK, "&Send Suggestion")
        self._send.SetHelpText(
            "Checks what you typed, then opens your mail program with the suggestion "
            "written to support@community-access.org. Nothing is sent until you "
            "press Send there."
        )
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cl&ose")
        cancel.SetHelpText("Closes without sending anything.")
        buttons.AddStretchSpacer()
        buttons.Add(self._send, 0, wx.RIGHT, 6)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizerAndFit(root)
        self._send.Bind(wx.EVT_BUTTON, lambda _e: self._submit())
        apply_modal_ids(self.dialog, affirmative_id=self._send.GetId(), escape_id=cancel.GetId())
        try:
            self._host._show_modal_dialog(self.dialog, TITLE)
        finally:
            self.dialog.Destroy()

    # -- fields -----------------------------------------------------------------

    def _field(self, grid: Any, label: str, help_text: str, *, multiline: bool = False) -> Any:
        wx = self._wx
        # Label before field, always: the dialog z-order gate reads tab order,
        # and a screen reader names a field from the static text before it.
        grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        style = wx.TE_MULTILINE if multiline else 0
        control = wx.TextCtrl(self.dialog, style=style, size=(340, 66 if multiline else -1))
        control.SetName(help_text)
        control.SetHelpText(help_text)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _choice(self, grid: Any, label: str, options: list[str], help_text: str) -> Any:
        wx = self._wx
        grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        control = wx.Choice(self.dialog, choices=options)
        control.SetSelection(0)
        control.SetName(help_text)
        control.SetHelpText(help_text)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _suggestion(self) -> Suggestion:
        index = max(0, self._kind.GetSelection())
        return Suggestion(
            type=_KINDS[index][1],
            title=self._title_ctrl.GetValue().strip(),
            url=self._url.GetValue().strip(),
            description=self._description.GetValue().strip(),
            language=self._language.GetValue().strip(),
            why=self._why.GetValue().strip(),
        )

    # -- sending ----------------------------------------------------------------

    def _submit(self) -> None:
        suggestion = self._suggestion()
        from quill.core.community_picks import load_bundled

        result = validate(suggestion, known_urls=known_urls(load_bundled()))
        if not result.ok:
            # Spoken and shown: the first problem is the one to fix, and a list
            # of six read out at once is a list nobody retains.
            self._host._announce(result.errors[0])
            self._host._show_message_box(
                "\n".join(result.errors), TITLE, self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        message = support_message(suggestion, product=self._app_label())
        if send_by_mail(self._host, message, title=TITLE, opened=OPENED):
            self.dialog.EndModal(self._wx.ID_OK)

    def _app_label(self) -> str:
        version = getattr(self._host, "_app_version", "") or ""
        return f"Quill Radio {version}".strip()


__all__ = ["OPENED", "TITLE", "open_suggest_dialog"]
