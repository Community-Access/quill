"""AI response dialog — read-only display of a single-shot AI result.

Shows an AI response with Copy to Clipboard and OK, used by the inline AI
actions, grammar check, and prompt/skill runs.

The former **Ask AI** chat dialog was retired here into the unified **Ask Quill**
companion: Ask Quill is now the one, context-aware chat door, so a second generic
chat surface no longer exists. ``A11Y-4`` hardened: ``apply_modal_ids``, public
``show()``/``close()``, dialog inventory.
"""

from __future__ import annotations

import wx

from quill.core.i18n import _
from quill.ui.dialog_contract import apply_modal_ids


class AIResponseDialog:
    """Read-only response dialog with Copy to Clipboard and OK button."""

    def __init__(
        self,
        parent: object,
        response: str,
        model_id: str,
        provider_label: str,
    ) -> None:
        self._response = response

        self.dialog = wx.Dialog(
            parent,
            title=_("AI Response"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 440))

        root = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(
            self.dialog,
            label=_("Model: {model}  (via {provider})").format(
                model=model_id, provider=provider_label
            ),
        )
        root.Add(info, 0, wx.ALL, 8)

        self._text_ctrl = wx.TextCtrl(
            self.dialog,
            value=response,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._text_ctrl.SetName("AI response")
        root.Add(self._text_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self.dialog, label=_("&Copy to Clipboard"))
        self._ok_btn = wx.Button(self.dialog, id=wx.ID_OK, label=_("&OK"))
        btn_row.Add(self._copy_btn, 0, wx.RIGHT, 4)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._ok_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label=_("OK"),
            cancel_id=wx.ID_OK,
            cancel_label=_("OK"),
        )

        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._ok_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_OK))
        self._text_ctrl.SetFocus()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    def _on_copy(self, _event: object) -> None:
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self._response))
            wx.TheClipboard.Close()
