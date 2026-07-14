"""Accessible "Font..." dialog for the hidden-codes run formatting.

The Format menu offers preset font/size/color submenus; this dialog is the
"More..." surface for arbitrary values (the design's open question). It is
deliberately keyboard- and screen-reader-first: every value is entered through a
labelled combo box, spin control or choice rather than a visual swatch picker, and
text color accepts either a named color or a ``#RRGGBB`` hex string typed directly
(so there is no nested, mouse-oriented color dialog to trap focus).

The caller owns the ``wx.Dialog`` (so the hardened modal path and
``apply_modal_ids`` live in one place); on OK the chosen attributes are exposed as
``result`` — a ``{key: value}`` map ready for
:func:`quill.core.tagging.build_span_insertion`.
"""

from __future__ import annotations

from typing import Any

_FONT_PRESETS = ("Arial", "Calibri", "Times New Roman", "Courier New", "Verdana", "Georgia")
# Named text colors -> hex, offered in the editable color combo (a typed #RRGGBB
# is accepted verbatim too).
_COLOR_NAMES = {
    "black": "#000000",
    "red": "#C00000",
    "green": "#008000",
    "blue": "#0000FF",
    "orange": "#FF8C00",
    "purple": "#800080",
}
_HIGHLIGHT_CHOICES = ("(none)", "Yellow", "Green", "Turquoise", "Pink", "Gray")


def _resolve_color(text: str) -> str:
    value = text.strip()
    if not value:
        return ""
    named = _COLOR_NAMES.get(value.lower())
    if named:
        return named
    if value.startswith("#"):
        return value
    return value


class FontFormatDialog:
    """Builds the Font dialog controls and exposes the chosen attributes after OK."""

    def __init__(self, wx: Any, *, current: dict[str, str] | None = None) -> None:
        self._wx = wx
        self._current = current or {}
        self.result: dict[str, str] | None = None
        self.dialog: Any = None
        self._outer_sizer: Any = None

    def populate(self, dlg: Any) -> Any:
        wx = self._wx
        self.dialog = dlg
        outer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(0, 2, 8, 10)
        grid.AddGrowableCol(1, 1)

        def _add(label_text: str, make_control: Any) -> Any:
            # Create the label BEFORE its control so the StaticText precedes the
            # control in the child-window z-order (== creation order in wxPython).
            # Screen readers use that order to associate labels with controls, so
            # the factory must run after the label (the A11Y z-order contract).
            grid.Add(wx.StaticText(dlg, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)
            control = make_control()
            grid.Add(control, 0, wx.EXPAND)
            return control

        self._family = _add(
            "Font &family (blank to leave unchanged):",
            lambda: wx.ComboBox(dlg, choices=list(_FONT_PRESETS), style=wx.CB_DROPDOWN),
        )
        self._size = _add(
            "Font &size in points (0 to leave unchanged):",
            lambda: wx.SpinCtrl(dlg, min=0, max=96),
        )
        color_choices = [""] + [name.title() for name in _COLOR_NAMES]
        self._color = _add(
            "Text &color (name or #RRGGBB; blank for none):",
            lambda: wx.ComboBox(dlg, choices=color_choices, style=wx.CB_DROPDOWN),
        )
        self._highlight = _add(
            "&Highlight:",
            lambda: wx.Choice(dlg, choices=list(_HIGHLIGHT_CHOICES)),
        )
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        self._outer_sizer = outer
        return outer

    def finalize(self) -> None:
        self.dialog.SetSizerAndFit(self._outer_sizer)
        self._family.SetValue(self._current.get("font-family", ""))
        size = self._current.get("font-size", "")
        self._size.SetValue(int(size) if size.isdigit() else 0)
        self._color.SetValue(self._current.get("color", ""))
        self._highlight.SetSelection(0)
        self.dialog.Bind(self._wx.EVT_BUTTON, self._on_ok, id=self._wx.ID_OK)

    def _on_ok(self, event: Any) -> None:
        attrs: dict[str, str] = {}
        family = self._family.GetValue().strip()
        if family:
            attrs["font-family"] = family
        size = int(self._size.GetValue())
        if size > 0:
            attrs["font-size"] = str(size)
        color = _resolve_color(self._color.GetValue())
        if color:
            attrs["color"] = color
        highlight = self._highlight.GetStringSelection()
        if highlight and highlight != "(none)":
            attrs["highlight"] = highlight.lower()
        self.result = attrs
        event.Skip()  # let the dialog close with ID_OK
