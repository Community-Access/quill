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


#: Focusable controls with no label of their own, which therefore need their
#: ``SetName`` published to the accessibility layer. A CheckBox, RadioButton or
#: Button is not here: its label *is* its name and already reaches the reader.
_UNLABELLED_CONTROLS = (
    wx.Choice,
    wx.ComboBox,
    wx.ListBox,
    wx.SpinCtrl,
    wx.SpinCtrlDouble,
    wx.TextCtrl,
)

#: The names wx gives a control nobody named. They say what the widget is,
#: which the reader already announces from the role, so they are not names.
_WX_DEFAULT_NAMES = frozenset({
    "choice",
    "combobox",
    "listbox",
    "text",
    "wxspinctrl",
    "wxspinctrldouble",
    "panel",
    "",
})


def publish_accessible_names(page: wx.Window) -> int:
    """State each control's existing name to the accessibility layer.

    The wizard pages already name their controls -- "Engine", "Voice", "Rate
    (WPM)", "Casting rules" -- with ``SetName``. That call sets the internal
    ``FindWindowByName`` key; it does **not** reliably reach MSAA/UIA. The
    nightly UIA run found six focusable controls on the Voices page reporting
    an empty ``Name`` (a spin control's Edit and Spinner, two Choice controls
    with their inner Text), so a screen reader arriving at one has nothing to
    say but "combo box" even though the name was written years ago.

    So this publishes what is already there, through
    :func:`set_accessible_name`, which attaches the ``wx.Accessible`` that
    states the name outright. It does **not** invent names: an earlier draft
    derived them from the preceding ``wx.StaticText`` and made things worse --
    the casting pattern field, authored as "Casting pattern (title glob or
    #number)", would have been renamed to the entire three-sentence paragraph
    above it, which a reader would then say in full on every visit.

    Run once per page by the wizard rather than as a call beside each of a
    hundred constructions -- which is also impossible in
    ``pages_documents.py``, a file sitting exactly on its GATE-11 budget.

    Skipped: a control still carrying wx's class default ("choice", "text"),
    because publishing that would turn "unnamed" into "named badly" and silence
    the gate that would otherwise catch it; and a control that already has a
    helper, so a deliberate ``set_accessible_name`` upstream always wins.

    Returns the number published, so a test can tell "nothing needed doing"
    from "the walk found nothing".
    """
    published = 0
    for child in page.GetChildren():
        if not isinstance(child, _UNLABELLED_CONTROLS):
            continue
        if getattr(child, "_a11y_helper", None) is not None:
            continue
        name = (child.GetName() or "").strip()
        if name.lower() in _WX_DEFAULT_NAMES:
            continue
        set_accessible_name(child, name)
        published += 1
    return published


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
