"""Verbosity Safe Mode / reset dialog (verbosity §29).

A one-stop escape hatch: temporarily disable custom verbosity, reset the selected
verb or chord, or restore built-in defaults — all non-destructive (the user is
asked to export first if they want a backup). Backed by the pure
:mod:`quill.core.verbosity.safe_mode` helpers; the actual export is delegated to
a callback. A11Y-4 hardened.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.ui.dialog_contract import apply_modal_ids, show_message_box

__all__ = ["VerbositySafeModeDialog"]

# Action ids the dialog returns to the caller via :attr:`action`.
ACTION_DISABLE_CUSTOM = "disable_custom"
ACTION_RESET_VERB = "reset_verb"
ACTION_RESET_CHORD = "reset_chord"
ACTION_RESTORE_BUILTIN = "restore_builtin"
ACTION_EXPORT = "export"


class VerbositySafeModeDialog:
    """Offer scoped, non-destructive verbosity resets."""

    def __init__(
        self,
        parent: object,
        *,
        announce_cb: Callable[[str], None] | None = None,
        export_cb: Callable[[], None] | None = None,
    ) -> None:
        self._announce = announce_cb or (lambda _m: None)
        self._export = export_cb
        self._action: str | None = None

        self.dialog = wx.Dialog(parent, title="Verbosity Safe Mode", style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "Safe Mode falls back to built-in verbosity without deleting your\n"
                "customizations. Export first if you want a backup."
            ),
        )
        root.Add(intro, 0, wx.ALL, 10)

        self._export_btn = wx.Button(self.dialog, label="&Export current settings first...")
        self._disable_btn = wx.Button(self.dialog, label="&Disable custom verbosity temporarily")
        self._reset_verb_btn = wx.Button(self.dialog, label="Reset selected &verb")
        self._reset_chord_btn = wx.Button(self.dialog, label="Reset selected &chord")
        self._restore_btn = wx.Button(self.dialog, label="&Restore built-in defaults")
        for b in (
            self._export_btn,
            self._disable_btn,
            self._reset_verb_btn,
            self._reset_chord_btn,
            self._restore_btn,
        ):
            root.Add(b, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="C&lose")
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

        self._export_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_export())
        self._disable_btn.Bind(wx.EVT_BUTTON, lambda _e: self._finish(ACTION_DISABLE_CUSTOM))
        self._reset_verb_btn.Bind(wx.EVT_BUTTON, lambda _e: self._finish(ACTION_RESET_VERB))
        self._reset_chord_btn.Bind(wx.EVT_BUTTON, lambda _e: self._finish(ACTION_RESET_CHORD))
        self._restore_btn.Bind(wx.EVT_BUTTON, lambda _e: self._confirm_restore())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

    def _on_export(self) -> None:
        if self._export is not None:
            self._export()
        self._action = ACTION_EXPORT
        self._announce("Exported current verbosity settings.")

    def _confirm_restore(self) -> None:
        confirm = show_message_box(
            "Restore built-in verbosity defaults? Your customizations are kept on disk "
            "but will no longer apply until re-enabled.",
            "Restore defaults",
            wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT,
            self.dialog,
        )
        if confirm == wx.ID_YES:
            self._finish(ACTION_RESTORE_BUILTIN)

    def _finish(self, action: str) -> None:
        self._action = action
        self._announce(f"Safe Mode: {action.replace('_', ' ')}.")
        self.dialog.EndModal(wx.ID_OK)

    @property
    def action(self) -> str | None:
        """The reset action the user chose, or ``None`` if they just closed."""
        return self._action

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CLOSE)
