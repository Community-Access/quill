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
        self, grid: wx.FlexGridSizer, text: str, value: int, *, hi: int = 10000, help_text: str = ""
    ) -> wx.SpinCtrl:
        grid.Add(wx.StaticText(self, label=text), 0, wx.ALIGN_CENTER_VERTICAL)
        spin = wx.SpinCtrl(self, min=0, max=hi, initial=int(value))
        set_accessible_name(spin, text.replace("&", ""))
        if help_text:
            spin.SetHelpText(help_text)
        grid.Add(spin, 0)
        return spin


class _Named(wx.Accessible):
    """Gives a control a real accessible name, not just a window name.

    Adopted from podHarvest as part of the shared tag-and-chapter work (see
    ``docs/superpowers/specs/ALIGNMENT-audio-tags-and-chapters.md``):
    ``SetName`` sets the internal ``FindWindowByName`` key, and Windows will
    often derive a name from a preceding ``wx.StaticText``, but neither
    reliably reaches MSAA/UIA, AT-SPI or NSAccessibility for a control with no
    adjacent label. Implementing ``wx.Accessible`` states the name outright
    rather than hoping a heuristic finds it.
    """

    def __init__(self, name: str) -> None:
        super().__init__()
        self._name = name

    def GetName(self, childId: int) -> tuple[int, str]:  # noqa: N802,N803 - wx API casing
        return (wx.ACC_OK, self._name)


def set_accessible_name(ctrl: wx.Window, name: str) -> None:
    """Name a control for screen readers, three ways, because one is not enough.

    ``wx.SpinCtrl``/``wx.SpinCtrlDouble`` wrap a child ``TextCtrl`` (the
    focusable edit); the composite's own name does not propagate to it, so a
    screen reader reads the field unnamed unless the child is named too.

    On top of that the control gets a ``wx.Accessible`` helper stating the
    name directly. ``SetAccessible`` does not take ownership, so the helper is
    stashed on the control -- without that reference it is garbage collected
    and the name silently disappears, which is the worst shape of
    accessibility bug: one that tests as present and speaks as absent.
    """
    ctrl.SetName(name)
    for child in getattr(ctrl, "GetChildren", list)():
        if isinstance(child, wx.TextCtrl):
            child.SetName(name)
    try:
        helper = _Named(name)
        ctrl.SetAccessible(helper)
        ctrl._a11y_helper = helper  # noqa: SLF001 - keep a strong reference alive
    except (AttributeError, NotImplementedError):
        # wx.Accessible is Windows-only; elsewhere the label heuristic and the
        # platform's own defaults apply, exactly as they did before this.
        pass
