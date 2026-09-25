"""The File Format dialog: what this document saves as (bad.md P1.8, 3.7).

QUILL Lite has had one window for this on ``Ctrl+Alt+E`` since it shipped. QUILL
had two status-bar cells and no dialog at all -- the encoding and the line
ending could be *read* from the bar and changed nowhere, which is the shape of
a setting that exists without being reachable.

Both halves live in one window because they are one question ("how does this
file get written?") and because they are asked at the same moment: a file
arriving from somewhere else is usually wrong in both ways at once.

The choice lists are the shared ``quill.core.lite.textfile`` ones, so the two
editors offer the same four encodings under the same names -- Notepad's names,
so somebody who has seen its Save As dialog recognises them.
"""

from __future__ import annotations

import wx

from quill.core.lite.textfile import (
    encoding_rows,
    newline_rows,
)
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["FileFormatDialog", "describe_encoding", "describe_line_ending"]

_PAD = 8


def _index_of(choices: tuple[tuple[str, str], ...], value: str) -> int:
    for index, (candidate, _name) in enumerate(choices):
        if candidate == value:
            return index
    return 0


def describe_encoding(codec: str) -> str:
    """The speakable name for *codec*, or the codec itself if it is not offered.

    Reads the same rows the chooser builds, so an encoding QUILL can read but
    does not offer -- UTF-16 big-endian, say -- is named rather than spelled out
    as a codec string (bad.md F8).
    """
    for candidate, name in encoding_rows(codec):
        if candidate == codec:
            return name.removesuffix(" (keep as is)")
    return codec


def describe_line_ending(value: str) -> str:
    """The speakable name for a line ending, e.g. "CRLF (Windows)"."""
    if not value:
        return "Unknown"
    for candidate, name in newline_rows(value):
        if candidate == value:
            return name.removesuffix(" (keep as is)")
    return "Unknown"


class FileFormatDialog:
    """Choose the encoding and the line endings this document saves with."""

    def __init__(self, parent: object, *, encoding: str, line_ending: str) -> None:
        self.dialog = wx.Dialog(parent, title="File Format", style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label="These take effect the next time you save this document.",
            ),
            0,
            wx.ALL,
            _PAD,
        )

        # The document's own encoding and line endings are rows here when the
        # chooser does not otherwise offer them: selecting a missing index fell
        # back to 0, which is UTF-8 and CRLF, so a UTF-16 big-endian or
        # classic-Mac CR file described itself wrongly and OK converted it
        # (bad.md F8).
        self._encoding_rows = encoding_rows(encoding)
        self._newline_rows = newline_rows(line_ending)

        root.Add(wx.StaticText(self.dialog, label="&Encoding:"), 0, wx.LEFT | wx.TOP, _PAD)
        self._encoding = wx.Choice(
            self.dialog, choices=[name for _codec, name in self._encoding_rows]
        )
        self._encoding.SetName("Encoding")
        self._encoding.SetHelpText(
            "How characters are stored. UTF-8 is the right answer for anything new. "
            "UTF-8 with BOM is what some Windows tools expect. Windows-1252 is the "
            "old Western European encoding a lot of existing .txt files are in. A "
            "'keep as is' row means this file arrived in something else, which QUILL "
            "reads and writes back but does not offer as a new choice."
        )
        self._encoding.SetSelection(_index_of(self._encoding_rows, encoding))
        root.Add(self._encoding, 0, wx.EXPAND | wx.ALL, _PAD)

        root.Add(wx.StaticText(self.dialog, label="&Line endings:"), 0, wx.LEFT | wx.TOP, _PAD)
        self._line_ending = wx.Choice(
            self.dialog, choices=[name for _value, name in self._newline_rows]
        )
        self._line_ending.SetName("Line endings")
        self._line_ending.SetHelpText(
            "CRLF is what Windows programs write. LF is what Unix, macOS and most "
            "build tools expect. QUILL writes back whichever the file arrived with "
            "unless you change it here."
        )
        self._line_ending.SetSelection(_index_of(self._newline_rows, line_ending))
        root.Add(self._line_ending, 0, wx.EXPAND | wx.ALL, _PAD)

        buttons = self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        # EXPAND, not ALIGN_RIGHT: the dialog contract (A11Y-4) wants the button
        # row to span, so the tab order and the reading order agree.
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self._encoding.SetFocus()

    def show(self) -> int:
        """Show it through the shared modal path, and return the answer.

        The dialog owns its own showing (the hardening contract): a surface
        whose caller decides how to show it is a surface that gets shown the
        wrong way exactly once, in the one place nobody re-reads.
        """
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(self.dialog, "File Format"))

    @property
    def choices(self) -> tuple[str, str]:
        """The chosen ``(encoding, line_ending)``."""
        return (
            self._encoding_rows[max(0, self._encoding.GetSelection())][0],
            self._newline_rows[max(0, self._line_ending.GetSelection())][0],
        )

    def close(self) -> None:
        self.dialog.Destroy()
