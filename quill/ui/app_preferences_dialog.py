"""A small, generic Preferences dialog (Ctrl+,) for the standalone companion
apps (Quill Radio, QUILL Cast) -- a short list of app-level startup toggles
(Resume on Launch, Check for Updates on Startup, ...). Each app supplies its
own checkbox specs and applies the returned values back to its own settings
store; this dialog holds no app-specific knowledge.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(slots=True)
class PreferenceCheckbox:
    """One checkbox: the visible label, its accessible name, and the
    starting value. ``name`` carries the ``&`` mnemonic; ``help_text`` is the
    fuller accessible description set via ``SetName``."""

    name: str
    help_text: str
    value: bool


class PreferencesDialog:
    """Returns the updated bool values (same order as the input specs), or
    ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        app_title: str,
        checkboxes: list[PreferenceCheckbox],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: list[bool] | None = None
        self._checks: list[wx.CheckBox] = []

        self.dialog = wx.Dialog(
            parent, title=f"{app_title} Preferences", style=wx.DEFAULT_DIALOG_STYLE
        )
        root = wx.BoxSizer(wx.VERTICAL)

        for spec in checkboxes:
            check = wx.CheckBox(self.dialog, label=spec.name)
            check.SetName(spec.help_text)
            check.SetValue(spec.value)
            root.Add(check, 0, wx.ALL, 8)
            self._checks.append(check)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = wx.Button(self.dialog, wx.ID_OK, "&Save")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.AddStretchSpacer()
        btn_row.Add(save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        root.Fit(self.dialog)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def _on_save(self, _event: object) -> None:
        self._result = [check.GetValue() for check in self._checks]
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> list[bool] | None:
        from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(
                self.dialog, f"{self.dialog.GetTitle()}", announce=self._announce
            )
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()
