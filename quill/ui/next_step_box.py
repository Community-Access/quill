"""A failure box that offers the one next step (FUX-16).

"Something failed. I don't know whether to retry or start over." An OK-only
box with the exception's text in it answers neither half: OK does nothing
about the problem, and the text is written for whoever fixes the code. This
box says what happened and what was kept in plain words, and offers:

* the one most useful next step as its default button (Retry, Choose Another
  File, Save As, Sign In Again, Open Settings), when there is one;
* Show Details and Copy Details: the technical text, versions and the error,
  redacted, which the person can read and edit before copying. Nothing is
  sent anywhere;
* Close, which carries no access key (Escape is Close; GATE-14).

The words come from :mod:`quill.core.command_failure`; this module only shows
them. It is not a framework: a caller that already has a good box keeps it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["NextStepBox", "show_next_step"]

#: What Copy Details says, once: the clipboard changed, and nothing left the machine.
COPIED = "Details copied. Nothing was sent."


class NextStepBox:
    """The dialog and its controls, built but not shown, so tests can drive it."""

    def __init__(
        self,
        parent: Any,
        message: str,
        caption: str,
        *,
        next_label: str = "",
        next_help: str = "",
        details: str = "",
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
        from quill.ui.dpi import dip_size

        self._announce = announce
        self.dialog = wx.Dialog(parent, title=caption, style=wx.DEFAULT_DIALOG_STYLE)
        dialog = self.dialog
        dialog.SetMinSize(dip_size(dialog, 420, -1))
        root = wx.BoxSizer(wx.VERTICAL)
        self.message = wx.StaticText(dialog, label=message)
        self.message.Wrap(dialog.FromDIP(420))
        root.Add(self.message, 0, wx.EXPAND | wx.ALL, 12)

        self.details_label = wx.StaticText(
            dialog, label="Details (you can edit them before copying):"
        )
        self.details = wx.TextCtrl(dialog, value=details, style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
        self.details.SetName("Details")
        self.details.SetHelpText(
            "The technical text: the app's version, Windows, and the error. "
            "Edit out anything you do not want to share, then Copy Details. "
            "Nothing is sent anywhere."
        )
        self.details.SetMinSize(dip_size(dialog, -1, 100))
        self.details_label.Hide()
        self.details.Hide()
        root.Add(self.details_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        root.Add(self.details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.next_button: Any = None
        if next_label:
            self.next_button = wx.Button(dialog, wx.ID_OK, label=next_label)
            self.next_button.SetHelpText(
                next_help or f"Closes this message and does this: {next_label.replace('&', '')}."
            )
            buttons.Add(self.next_button, 0, wx.RIGHT, 8)
        self.show_button: Any = None
        self.copy_button: Any = None
        if details:
            self.show_button = wx.Button(dialog, label="Show &Details")
            self.show_button.SetHelpText("Shows the technical text, so you can read or edit it.")
            self.show_button.Bind(wx.EVT_BUTTON, self._on_show)
            buttons.Add(self.show_button, 0, wx.RIGHT, 8)
            self.copy_button = wx.Button(dialog, label="&Copy Details")
            self.copy_button.SetHelpText(
                "Copies the technical text to the clipboard for a support report. "
                "Nothing is sent anywhere."
            )
            self.copy_button.Bind(wx.EVT_BUTTON, self._on_copy)
            buttons.Add(self.copy_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer()
        self.close_button = wx.Button(dialog, wx.ID_CANCEL, label="Close")
        self.close_button.SetHelpText("Closes this message without doing anything else.")
        buttons.Add(self.close_button, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        dialog.SetSizer(root)
        dialog.Fit()
        bind_close_button(dialog, self.close_button, modeless=False)
        default = self.next_button or self.close_button
        default.SetDefault()
        default.SetFocus()
        apply_modal_ids(
            dialog,
            affirmative_id=wx.ID_OK if self.next_button is not None else wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        dialog.CentreOnParent()

    def _on_show(self, _event: object = None) -> None:
        visible = not self.details.IsShown()
        self.details_label.Show(visible)
        self.details.Show(visible)
        self.show_button.SetLabel("Hide &Details" if visible else "Show &Details")
        self.dialog.Layout()
        self.dialog.Fit()
        if visible:
            self.details.SetFocus()

    def copy(self) -> bool:
        """Put the details, as the person left them, on the clipboard."""
        from quill.ui.say_commands import set_clipboard_text

        copied = set_clipboard_text(self.details.GetValue())
        if self._announce is not None:
            self._announce(COPIED if copied else "The clipboard is busy. Nothing was copied.")
        return copied

    def _on_copy(self, _event: object = None) -> None:
        self.copy()


def show_next_step(
    parent: Any,
    message: str,
    caption: str,
    *,
    next_label: str = "",
    next_help: str = "",
    details: str = "",
    announce: Callable[[str], None] | None = None,
    show_modal: Callable[[Any, str], int] | None = None,
) -> bool:
    """Show the box; return True when the person chose the next step.

    *show_modal* is the host's own ``_show_modal_dialog`` where it has one, so
    focus returns to the control that was in use and the entry and exit cues
    follow the person's setting; otherwise the shared ``show_modal_dialog``.
    """
    import wx

    from quill.ui.dialog_contract import show_modal_dialog

    box = NextStepBox(
        parent,
        message,
        caption,
        next_label=next_label,
        next_help=next_help,
        details=details,
        announce=announce,
    )
    try:
        if show_modal is not None:
            result = show_modal(box.dialog, caption)
        else:
            result = show_modal_dialog(box.dialog, caption, announce=announce)
    finally:
        box.dialog.Destroy()
    return bool(next_label) and result == wx.ID_OK
