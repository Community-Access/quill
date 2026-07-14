"""QVP install dialog (verbosity §21).

Pick a ``.qvp.json`` file, validate and install it through the pure
:func:`quill.core.verbosity.qvp.install_pack`, and read back the spoken sequence,
the accepted templates, anything rejected (with reasons), and any dependency
warnings. No pack content is executed. A11Y-4 hardened.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.verbosity.qvp import QVPInstallResult, install_pack
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["VerbosityQvpInstallDialog"]


class VerbosityQvpInstallDialog:
    """Install a QUILL Verbosity Pack from a file."""

    def __init__(
        self,
        parent: object,
        *,
        installed_template_ids: tuple[str, ...] = (),
        available_packs: tuple[str, ...] = (),
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._installed_ids = installed_template_ids
        self._available = available_packs
        self._announce = announce_cb or (lambda _m: None)
        self._result: QVPInstallResult | None = None

        self.dialog = wx.Dialog(
            parent, title="Install verbosity pack", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(520, 380))
        root = wx.BoxSizer(wx.VERTICAL)

        path_row = wx.BoxSizer(wx.HORIZONTAL)
        path_row.Add(
            wx.StaticText(self.dialog, label="&Pack file:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._path = wx.TextCtrl(self.dialog, style=wx.TE_READONLY)
        self._path.SetName("Selected pack file")
        path_row.Add(self._path, 1, wx.RIGHT, 6)
        self._browse_btn = wx.Button(self.dialog, label="&Browse...")
        path_row.Add(self._browse_btn, 0)
        root.Add(path_row, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self.dialog, label="&Result:"), 0, wx.LEFT | wx.TOP, 8)
        self._result_ctrl = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._result_ctrl.SetName("Install result")
        self._result_ctrl.SetMinSize(wx.Size(-1, 200))
        root.Add(self._result_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._install_btn = wx.Button(self.dialog, id=wx.ID_OK, label="&Install")
        self._install_btn.Disable()
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Cancel")
        btns.AddStretchSpacer()
        btns.Add(self._install_btn, 0, wx.RIGHT, 6)
        btns.Add(cancel_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Install",
            cancel_id=wx.ID_CANCEL,
        )

        self._browse_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_browse())
        self._install_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_install())
        cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))

    def _on_browse(self) -> None:
        with wx.FileDialog(
            self.dialog,
            "Choose a verbosity pack",
            wildcard="QUILL Verbosity Pack (*.qvp.json)|*.qvp.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            self._path.SetValue(picker.GetPath())
            self._preview()

    def _preview(self) -> None:
        path = self._path.GetValue()
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as error:
            self._result_ctrl.SetValue(f"Could not read file: {error}")
            self._install_btn.Disable()
            return
        result = install_pack(
            text,
            installed_template_ids=self._installed_ids,
            available_packs=self._available,
        )
        self._result = result
        self._render(result)
        self._install_btn.Enable(result.ok and bool(result.accepted))

    def _render(self, result: QVPInstallResult) -> None:
        lines = list(result.spoken_sequence)
        if result.accepted:
            lines.append("")
            lines.append("Accepted templates:")
            lines.extend(f"  - {tpl.name} ({tpl.applies_to})" for tpl in result.accepted)
        if result.rejected_templates:
            lines.append("")
            lines.append("Skipped:")
            lines.extend(f"  - {tid}: {reason}" for tid, reason in result.rejected_templates)
        if result.warnings:
            lines.append("")
            lines.extend(result.warnings)
        if result.errors:
            lines.append("")
            lines.extend(f"Error: {e}" for e in result.errors)
        self._result_ctrl.SetValue("\n".join(lines))
        for line in result.spoken_sequence:
            self._announce(line)

    def _on_install(self) -> None:
        self.dialog.EndModal(wx.ID_OK)

    @property
    def result(self) -> QVPInstallResult | None:
        return self._result

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CANCEL)
