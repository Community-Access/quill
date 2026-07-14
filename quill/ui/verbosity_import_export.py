"""Verbosity profile import / export dialog (verbosity §30).

Export the current custom profile to a ``.quill-verbosity-profile.json`` file, or
import one. Imports are strictly data and schema-checked through the pure
:mod:`quill.core.verbosity.import_export` (no code is ever executed). A11Y-4
hardened.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.verbosity.import_export import ProfileImportError, from_json, to_json
from quill.core.verbosity.profiles import CustomProfile
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

__all__ = ["VerbosityImportExportDialog"]


class VerbosityImportExportDialog:
    """Import or export a verbosity profile as data-only JSON."""

    def __init__(
        self,
        parent: object,
        current: CustomProfile,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._current = current
        self._announce = announce_cb or (lambda _m: None)
        self._imported: CustomProfile | None = None

        self.dialog = wx.Dialog(
            parent, title="Import / export verbosity profile", style=wx.DEFAULT_DIALOG_STYLE
        )
        root = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(
            self.dialog,
            label=(
                "Profiles are shared as .quill-verbosity-profile.json files.\n"
                "Imports are data only and validated; they never run code."
            ),
        )
        root.Add(info, 0, wx.ALL, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Import or export status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT, 10)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._export_btn = wx.Button(self.dialog, label="&Export...")
        self._import_btn = wx.Button(self.dialog, label="&Import...")
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="C&lose")
        btns.Add(self._export_btn, 0, wx.RIGHT, 6)
        btns.Add(self._import_btn, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

        self._export_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_export())
        self._import_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_import())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _on_export(self) -> None:
        with wx.FileDialog(
            self.dialog,
            "Export verbosity profile",
            defaultFile=f"{self._current.name}.quill-verbosity-profile.json",
            wildcard="QUILL verbosity profile (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            target = Path(picker.GetPath())
        try:
            target.write_text(to_json(self._current), encoding="utf-8", newline="\n")
        except OSError as error:
            self._set_status(f"Export failed: {error}")
            return
        self._set_status(f"Exported profile to {target.name}.")

    def _on_import(self) -> None:
        with wx.FileDialog(
            self.dialog,
            "Import verbosity profile",
            wildcard="QUILL verbosity profile (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            source = Path(picker.GetPath())
        try:
            self._imported = from_json(source.read_text(encoding="utf-8"))
        except (OSError, ProfileImportError) as error:
            show_message_box(
                f"Could not import this profile: {error}",
                "Import failed",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
            )
            self._set_status("Import failed.")
            return
        self._set_status(f"Imported profile {self._imported.name}.")
        self.dialog.EndModal(wx.ID_OK)

    @property
    def imported(self) -> CustomProfile | None:
        return self._imported

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CLOSE)
