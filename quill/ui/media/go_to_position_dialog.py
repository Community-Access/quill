"""The accessible "Go to Position (H:M:S)" dialog (``player.md`` Section 9.8).

Engine-agnostic: it collects a target position and exposes it; the caller applies
the seek and announces the landing. Built to the desktop accessibility checklist:

* Three labeled ``wx.SpinCtrl`` fields (Hours / Minutes / Seconds) as the primary,
  most-accessible input, plus an optional single **Timecode** text field for power
  users (``1:23:45`` / ``83:45`` / ``5025`` / ``1h23m45s``).
* Every field has a preceding ``wx.StaticText`` label AND an explicit accessible
  name via :func:`quill.ui.dialog_contract.set_accessible_name`.
* Standard OK/Cancel via :func:`apply_modal_ids`; OK is the default button so
  Enter seeks. Shown through the caller's ``_show_modal_dialog`` (GATE-16).
* The requested position is clamped to the media duration with the pure, tested
  :func:`quill.core.media.clamp_position`; an out-of-range value is reported so
  the caller can announce "beyond the end - clamped to ...".

The parse/format/clamp logic lives in ``quill.core.media`` and is unit-tested;
this module is only the wx surface.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.i18n import _
from quill.core.media import (
    InvalidTimecodeError,
    clamp_position,
    format_timecode,
    parse_timecode,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


class GoToPositionDialog(wx.Dialog):
    """Collect an H:M:S (or timecode) target position for the media player."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        duration_ms: int,
        current_ms: int = 0,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, title=_("Go to Position"))
        self._duration_ms = max(0, int(duration_ms))
        self._announce = announce
        self._target_ms = 0
        self._clamped = False

        current = clamp_position(current_ms, self._duration_ms)
        max_hours = max(0, self._duration_ms // 3_600_000)

        outer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(rows=3, cols=2, vgap=6, hgap=8)
        self._hours = self._spin(grid, _("&Hours:"), maximum=max(max_hours, 99))
        self._minutes = self._spin(grid, _("&Minutes:"), maximum=59)
        self._seconds = self._spin(grid, _("&Seconds:"), maximum=59)
        self._hours.SetValue(current // 3_600_000)
        self._minutes.SetValue((current // 60_000) % 60)
        self._seconds.SetValue((current // 1_000) % 60)
        outer.Add(grid, 0, wx.ALL, 12)

        tc_label = wx.StaticText(self, label=_("Or &type a timecode (h:mm:ss):"))
        outer.Add(tc_label, 0, wx.LEFT | wx.RIGHT, 12)
        self._timecode = wx.TextCtrl(self)
        set_accessible_name(self._timecode, _("Timecode"))
        outer.Add(self._timecode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # A focusable, reviewable error line (empty until a bad timecode is entered).
        self._error = wx.StaticText(self, label="")
        outer.Add(self._error, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizerAndFit(outer)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        ok = self.FindWindowById(wx.ID_OK)
        if ok is not None:
            ok.SetDefault()
            ok.Bind(wx.EVT_BUTTON, self._on_ok)

    def _spin(self, grid: wx.FlexGridSizer, label: str, *, maximum: int) -> wx.SpinCtrl:
        static = wx.StaticText(self, label=label)
        spin = wx.SpinCtrl(self, min=0, max=maximum, initial=0)
        # Propagate the accessible name onto the spin's inner text control too.
        set_accessible_name(spin, label.replace("&", "").rstrip(":"))
        grid.Add(static, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(spin, 0, wx.EXPAND)
        return spin

    def _on_ok(self, _event: wx.CommandEvent) -> None:
        typed = self._timecode.GetValue().strip()
        if typed:
            try:
                requested = parse_timecode(typed)
            except InvalidTimecodeError:
                self._report_error(_("That timecode is not valid. Try a form like 1:23:45."))
                return
        else:
            requested = (
                self._hours.GetValue() * 3_600
                + self._minutes.GetValue() * 60
                + self._seconds.GetValue()
            ) * 1_000

        target = clamp_position(requested, self._duration_ms)
        self._target_ms = target
        self._clamped = target != requested
        self.EndModal(wx.ID_OK)

    def _report_error(self, message: str) -> None:
        self._error.SetLabel(message)
        self.Layout()
        if self._announce is not None:
            self._announce(message)
        self._timecode.SetFocus()

    def get_target_ms(self) -> int:
        """The chosen position in milliseconds, clamped to the media duration."""
        return self._target_ms

    def was_clamped(self) -> bool:
        """True when the requested position was beyond the media and got clamped."""
        return self._clamped

    def clamped_message(self) -> str:
        """A ready-to-speak note when the target was clamped, else ``""``."""
        if not self._clamped:
            return ""
        return _("Beyond the end - moved to {position}.").format(
            position=format_timecode(self._target_ms, always_hours=True)
        )


__all__ = ["GoToPositionDialog"]
