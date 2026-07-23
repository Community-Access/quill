"""Customize Features dialog for the standalone apps.

A simple, accessible checklist: one checkbox per switchable app area (Quill
Radio's Weather menu, its Record menu, and so on), each with a short
description. Unchecking an area turns it off; the app omits that area's menu the
next time it launches. Mirrors the shape of the weather Settings dialog and goes
through the shared modal contract. wx lives only here; the state is the wx-free
``core/app_features`` model the caller passes in and saves.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.app_features import AppArea, AppFeatureSettings
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


class AppFeaturesDialog:
    def __init__(
        self,
        parent: object,
        *,
        app_title: str,
        areas: Sequence[AppArea],
        settings: AppFeatureSettings,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._areas = list(areas)
        self._settings = settings
        self._announce = announce_cb or (lambda _m: None)
        self._saved = False
        self._checks: dict[str, object] = {}

        self.dialog = wx.Dialog(
            parent, title=f"Customize {app_title} Features", style=wx.DEFAULT_DIALOG_STYLE
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Turn parts of the app on or off. Unchecking an area removes its "
                    "whole menu the next time you open the app."
                ),
            ),
            0,
            wx.ALL,
            12,
        )

        for area in self._areas:
            box = wx.CheckBox(self.dialog, label=f"Enable {area.label}")
            box.SetValue(settings.is_enabled(area.id))
            set_accessible_name(box, f"Enable {area.label}")
            root.Add(box, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
            if area.description:
                hint = wx.StaticText(self.dialog, label=area.description)
                root.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 28)
            self._checks[area.id] = box

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer()
        ok = wx.Button(self.dialog, wx.ID_OK, "&Save")
        btn_row.Add(ok, 0, wx.RIGHT, 6)
        btn_row.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"))
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 12)

        self.dialog.SetSizer(root)
        root.Fit(self.dialog)
        ok.Bind(wx.EVT_BUTTON, lambda _e: self._save())

    def _save(self) -> None:
        for area_id, box in self._checks.items():
            self._settings.set_enabled(area_id, bool(box.GetValue()))
        self._saved = True
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> bool:
        """Modal; returns True if the user saved (caller then persists)."""
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
            cancel_id=self._wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Customize Features", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self._saved
