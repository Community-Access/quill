"""Shared base and small helpers for Audio Studio wizard pages.

Every page is a ``wx.Panel`` with a bold heading, a one-sentence purpose line
that screen readers encounter before any control (A11Y: context first), a
``collect`` hook that writes the page's choices into the run request, and an
optional ``is_valid`` gate that Next/Start consult.
"""

from __future__ import annotations

import wx

from quill.ui.audio_studio.request import BatchSpeechRequest


class StudioPage(wx.Panel):
    """Base for all Audio Studio wizard pages."""

    def __init__(self, parent: wx.Window, name: str, title: str, purpose: str) -> None:
        super().__init__(parent)
        self.SetName(name)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(self, label=title, name=f"{name}.heading")
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        self.sizer.Add(heading, flag=wx.ALL, border=12)
        if purpose:
            self.sizer.Add(
                wx.StaticText(self, label=purpose, name=f"{name}.purpose"),
                flag=wx.LEFT | wx.RIGHT | wx.BOTTOM,
                border=12,
            )
        self.SetSizer(self.sizer)

    # -- contract -----------------------------------------------------------

    def collect(self, req: BatchSpeechRequest) -> None:  # noqa: B027 - optional hook
        """Write this page's choices into *req*. Default: nothing to collect."""

    def is_valid(self) -> tuple[bool, str]:
        """Whether Next may leave this page; (False, message) blocks with *message*."""
        return True, ""

    def on_shown(self, req: BatchSpeechRequest) -> None:  # noqa: B027 - optional hook
        """Called just before the page is shown (e.g. to refresh a summary)."""

    # -- small builders shared by pages --------------------------------------

    def add_label(self, text: str) -> None:
        self.sizer.Add(wx.StaticText(self, label=text), 0, wx.LEFT | wx.TOP, 12)

    def add_ms_spin(
        self, grid: wx.FlexGridSizer, text: str, value: int, *, hi: int = 10000
    ) -> wx.SpinCtrl:
        grid.Add(wx.StaticText(self, label=text), 0, wx.ALIGN_CENTER_VERTICAL)
        spin = wx.SpinCtrl(self, min=0, max=hi, initial=int(value))
        set_accessible_name(spin, text.replace("&", ""))
        grid.Add(spin, 0)
        return spin


def set_accessible_name(ctrl: wx.Window, name: str) -> None:
    """Name a control for screen readers, reaching composite spinners' inner edit.

    ``wx.SpinCtrl``/``wx.SpinCtrlDouble`` wrap a child ``TextCtrl`` (the focusable
    edit); the composite's own name does not propagate to it, so a screen reader
    reads the field unnamed unless the child is named too.
    """
    ctrl.SetName(name)
    for child in getattr(ctrl, "GetChildren", list)():
        if isinstance(child, wx.TextCtrl):
            child.SetName(name)
