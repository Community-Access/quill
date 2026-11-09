"""The Language Servers window: which servers run, and what they are used for.

Shared by QUILL and QUILL Lite (Navigate > Code > Language Servers...). One
switch for all of them, one check box per server with whether it is here
(bundled with QUILL, installed on this computer, or not found), and one check
box per use: suggestions, problems, and parameter hints as you type. The
settings are the same names in both editors (:mod:`quill.ui.language_servers`).

OK keeps the choices; Cancel and Escape leave everything as it was. Nothing is
announced on opening: the reader says the window and the focused control
(GATE-13). Access keys are unique in the window (GATE-14).
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.lsp.servers import LANGUAGE_SERVERS
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.language_servers import FEATURE_SETTINGS, server_status

__all__ = ["LanguageServersDialog", "server_row"]

_ACCESS = {
    "language_server_completions": "Su&ggestions from language servers",
    "language_server_problems": "&Problems from language servers",
    "parameter_hints_as_you_type": "Parameter &hints as you type",
}


def server_row(spec: Any) -> str:
    """One row of the server list: its name, what it serves, and whether it is here."""
    serves = ", ".join(suffix.lstrip(".") for suffix in spec.suffixes)
    return f"{spec.name} ({serves}): {server_status(spec)}"


class LanguageServersDialog:
    """The window; :meth:`apply` writes the choices back to *settings*."""

    def __init__(self, parent: Any, settings: Any) -> None:
        self._settings = settings
        self.dialog = wx.Dialog(parent, title="Language Servers")
        root = wx.BoxSizer(wx.VERTICAL)
        pad = self.dialog.FromDIP(8)

        self.enabled = wx.CheckBox(self.dialog, label="&Use language servers")
        self.enabled.SetValue(bool(getattr(settings, "language_servers_enabled", True)))
        self.enabled.SetHelpText(
            "The one switch for all of them. Off, Word Prediction, Check This File "
            "and parameter hints use only QUILL's own checkers and the file's own "
            "names, and no server is ever started."
        )
        root.Add(self.enabled, 0, wx.ALL, pad)

        label = wx.StaticText(self.dialog, label="&Servers:")
        self.servers = wx.CheckListBox(
            self.dialog, choices=[server_row(spec) for spec in LANGUAGE_SERVERS]
        )
        self.servers.SetHelpText(
            "Each language server, what it reads, and whether it is here: bundled "
            "with QUILL, installed on this computer, or not found. Space checks or "
            "clears one. A server starts the first time you need it in a file it "
            "reads, never at launch, and stops when it has been idle a while. "
            "None of them uses the internet."
        )
        off = set(getattr(settings, "language_servers_off", []) or [])
        for index, spec in enumerate(LANGUAGE_SERVERS):
            self.servers.Check(index, spec.name not in off)
        root.Add(label, 0, wx.LEFT | wx.RIGHT, pad)
        root.Add(self.servers, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, pad)

        self.features: dict[str, wx.CheckBox] = {}
        for setting, _label, help_text in FEATURE_SETTINGS:
            box = wx.CheckBox(self.dialog, label=_ACCESS[setting])
            default = setting != "parameter_hints_as_you_type"
            box.SetValue(bool(getattr(settings, setting, default)))
            box.SetHelpText(help_text)
            self.features[setting] = box
            root.Add(box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, pad)

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self.dialog, wx.ID_OK, label="OK")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        ok.SetHelpText("Keep these choices.")
        cancel.SetHelpText("Close without changing anything.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, pad)
        self.dialog.SetSizerAndFit(root)
        self.dialog.SetMinSize(self.dialog.FromDIP(wx.Size(520, 420)))
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.enabled.SetFocus()

    def apply(self) -> None:
        """Write the window's choices back to the settings object."""
        settings = self._settings
        settings.language_servers_enabled = bool(self.enabled.GetValue())
        settings.language_servers_off = [
            spec.name
            for index, spec in enumerate(LANGUAGE_SERVERS)
            if not self.servers.IsChecked(index)
        ]
        for setting, box in self.features.items():
            setattr(settings, setting, bool(box.GetValue()))

    def destroy(self) -> None:
        self.dialog.Destroy()
