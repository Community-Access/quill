"""QUILL Lite's half of the Say commands: two hooks, and no commands of its own.

Say Clipboard, Append Selection to Clipboard, Save Clipboard to File, Clear
Clipboard, Say Time Then Date, Say Windows Open and Copy Log are
:class:`quill.ui.say_commands.SayCommandsMixin`'s, the same handlers QUILL runs
on the same keys. What lives here is only how this window shows the two things
it shows: the clipboard in the read-only text window every other QUILL Lite
readout uses, and the standard Save dialog. If this class ever grows a command
of its own, the feature has forked.
"""

from __future__ import annotations

from pathlib import Path

import wx

from quill.apps.lite_dialogs import show_text_window
from quill.ui.say_commands import SayCommandsMixin

__all__ = ["DocumentSayMixin"]


class DocumentSayMixin(SayCommandsMixin):
    """The shared Say commands, shown QUILL Lite's way."""

    def _say_show_text(self, title: str, text: str) -> None:
        show_text_window(self, title, text)  # type: ignore[arg-type]

    def _say_ask_save_path(self, suggested: str) -> Path | None:
        with wx.FileDialog(
            self,  # type: ignore[arg-type]
            "Save Clipboard to File",
            defaultDir=self._default_document_folder(),  # type: ignore[attr-defined]
            defaultFile=suggested,
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return Path(dialog.GetPath())
