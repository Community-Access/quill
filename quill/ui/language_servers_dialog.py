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


class LanguageServersDialog(wx.Dialog):
    """The window; :meth:`apply` writes the choices back to *settings*."""

    def __init__(self, parent: Any, settings: Any) -> None:
        self._settings = settings
        super().__init__(parent, title="Language Servers")
        self.dialog = self
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

        # One check box per server rather than a check list: screen readers do
        # not say a check list row's state as you arrow (A11Y-SR-1).
        label = wx.StaticText(self.dialog, label="Servers:")
        self.server_area = wx.ScrolledWindow(self.dialog, style=wx.VSCROLL)
        self.server_area.SetScrollRate(0, self.dialog.FromDIP(10))
        area = wx.BoxSizer(wx.VERTICAL)
        off = set(getattr(settings, "language_servers_off", []) or [])
        self.servers: list[wx.CheckBox] = []
        for spec in LANGUAGE_SERVERS:
            box = wx.CheckBox(self.server_area, label=server_row(spec))
            box.SetValue(spec.name not in off)
            box.SetHelpText(
                f"{spec.name}: checked, it runs when you need it in a file it reads, "
                "never at launch, and stops when it has been idle a while. It is "
                f"{server_status(spec)}. None of the servers uses the internet."
            )
            self.servers.append(box)
            area.Add(box, 0, wx.BOTTOM, pad // 2)
        self.server_area.SetSizer(area)
        root.Add(label, 0, wx.LEFT | wx.RIGHT, pad)
        root.Add(self.server_area, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, pad)

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
            for spec, box in zip(LANGUAGE_SERVERS, self.servers, strict=True)
            if not box.GetValue()
        ]
        for setting, box in self.features.items():
            setattr(settings, setting, bool(box.GetValue()))

    def destroy(self) -> None:
        self.Destroy()
