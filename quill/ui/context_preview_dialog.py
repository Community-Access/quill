"""Accessible "what will be sent" preview (Companion PRD §11 / Phase 2).

Before document text is sent to a provider, the user gets one accessible summary
of exactly what will leave — word/token counts, the file, whether the full
document is included, and whether a possible secret was redacted — and decides
Continue or Cancel. A "Show text" toggle reveals the full, already-redacted
payload in a read-only field for review.

The dialog is shown through ``MainFrame._show_modal_dialog`` (GATE-16: never a raw
``ShowModal``), so the keyboard/focus/announcement contract applies.
"""

from __future__ import annotations

from typing import Any

from quill.core.ai.context_builder import ContextPreview

__all__ = ["confirm_context_share"]


def confirm_context_share(
    controller: Any, preview: ContextPreview, *, title: str = "Context to share"
) -> bool:
    """Show the preview and return True if the user chose Continue.

    Must be called on the UI thread (the caller marshals if needed). Returns False
    on Cancel/Escape, so nothing is sent.
    """
    import wx

    dialog = wx.Dialog(
        controller.frame, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    dialog.SetSize((640, 480))
    outer = wx.BoxSizer(wx.VERTICAL)

    summary = wx.StaticText(dialog, label=preview.speakable_summary())
    summary.SetName("Context summary")
    summary.Wrap(580)
    outer.Add(summary, 0, wx.ALL, 12)

    full = wx.TextCtrl(
        dialog,
        value=preview.text,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
    )
    full.SetName("Full context text to be sent")
    full.Hide()
    outer.Add(full, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    show_btn = wx.Button(dialog, label="Show &Text")
    buttons.Add(show_btn, 0, wx.RIGHT, 8)
    buttons.AddStretchSpacer()
    cont_btn = wx.Button(dialog, wx.ID_OK, label="&Continue")
    cont_btn.SetDefault()
    buttons.Add(cont_btn, 0, wx.RIGHT, 8)
    buttons.Add(wx.Button(dialog, wx.ID_CANCEL, label="Cancel"), 0)
    outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
    dialog.SetSizer(outer)

    def on_toggle(_event: object) -> None:
        shown = not full.IsShown()
        full.Show(shown)
        show_btn.SetLabel("Hide &Text" if shown else "Show &Text")
        dialog.Layout()
        if shown:
            full.SetFocus()

    show_btn.Bind(wx.EVT_BUTTON, on_toggle)

    from quill.ui.dialog_contract import apply_modal_ids

    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    try:
        result = controller._show_modal_dialog(dialog, title)
        return bool(result == wx.ID_OK)
    finally:
        dialog.Destroy()
