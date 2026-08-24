"""Caption Settings: size, colour, background, opacity, position.

Section 508's 503.4.1 asks for user controls for captions. WCAG adds the two
things that decide whether captions are actually readable and that the law does
not spell out: **contrast** (1.4.3) and **scaling to 200% without loss** (1.4.4).
Both are here, and 300% is offered as well, because somebody who needs 200%
frequently needs more and a standard is a floor rather than a target.

Every control is a plain labelled ``wx.Choice`` or ``wx.Slider``. No colour
picker: a free choice of any two colours invites a combination that fails, and
the failure is silent until somebody cannot read a caption during something they
cared about. Three text colours and three backgrounds, all of which pass against
each other, is a smaller answer that is always right.

What the values mean lives in :mod:`quill.core.radio.caption_style`, which is
wx-free and tested; this is only the window.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.caption_style import (
    BACKGROUND_COLOURS,
    POSITIONS,
    SIZE_CHOICES,
    TEXT_COLOURS,
    CaptionStyle,
    describe,
)
from quill.ui.dialog_contract import apply_modal_ids


class CaptionSettingsDialog:
    """Adjust how captions look, and hear what you chose."""

    def __init__(
        self,
        parent: Any,
        *,
        style: CaptionStyle | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._style = (style or CaptionStyle()).clamped()
        self._show_modal_dialog = show_modal_dialog
        self._announce = announce or (lambda _m: None)

        self._dialog = wx.Dialog(parent, title="Caption Settings")
        grid = wx.FlexGridSizer(rows=5, cols=2, vgap=8, hgap=10)
        grid.AddGrowableCol(1, 1)

        self._size = self._row(grid, "Caption &size:", [f"{p}%" for p in SIZE_CHOICES])
        self._size.SetSelection(_index_of(SIZE_CHOICES, self._style.size_percent))

        self._text = self._row(grid, "&Text colour:", [label for label, _v in TEXT_COLOURS])
        self._text.SetSelection(_index_of([v for _l, v in TEXT_COLOURS], self._style.text_colour))

        self._back = self._row(
            grid, "&Background colour:", [label for label, _v in BACKGROUND_COLOURS]
        )
        self._back.SetSelection(
            _index_of([v for _l, v in BACKGROUND_COLOURS], self._style.background_colour)
        )

        grid.Add(
            wx.StaticText(self._dialog, label="Background &opacity:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._opacity = wx.Slider(
            self._dialog, value=self._style.background_opacity, minValue=0, maxValue=100
        )
        self._opacity.SetName(
            "Background opacity, 0 to 100 percent; solid is recommended for readable captions"
        )
        grid.Add(self._opacity, 1, wx.EXPAND)

        self._position = self._row(grid, "&Position:", [label for label, _v in POSITIONS])
        self._position.SetSelection(_index_of([v for _l, v in POSITIONS], self._style.position))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 12)
        root.Add(
            wx.StaticText(
                self._dialog,
                label=(
                    "A solid background is the default because caption text sits over\n"
                    "moving pictures, and no colour can be guaranteed to contrast with them."
                ),
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM,
            12,
        )

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = wx.Button(self._dialog, wx.ID_OK, "&Save")
        save_btn.SetHelpText(
            "Applies these caption looks to every video from now on, "
            "including one playing right now."
        )
        cancel_btn = wx.Button(self._dialog, wx.ID_CANCEL, "&Cancel")
        cancel_btn.SetHelpText("Closes without changing how captions look.")
        buttons.Add(save_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.ALL, 12)

        self._dialog.SetSizer(root)
        self._dialog.Fit()
        apply_modal_ids(self._dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _row(self, grid: Any, label: str, choices: list[str]) -> Any:
        wx = self._wx
        grid.Add(wx.StaticText(self._dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        control = wx.Choice(self._dialog, choices=choices)
        control.SetName(label.replace("&", "").rstrip(":"))
        grid.Add(control, 1, wx.EXPAND)
        return control

    @property
    def dialog(self) -> Any:
        return self._dialog

    def chosen(self) -> CaptionStyle:
        """The style the controls currently describe."""
        return CaptionStyle(
            size_percent=SIZE_CHOICES[max(0, self._size.GetSelection())],
            text_colour=TEXT_COLOURS[max(0, self._text.GetSelection())][1],
            background_colour=BACKGROUND_COLOURS[max(0, self._back.GetSelection())][1],
            background_opacity=int(self._opacity.GetValue()),
            position=POSITIONS[max(0, self._position.GetSelection())][1],
        ).clamped()

    def show(self) -> CaptionStyle | None:
        """Show the dialog. Returns the new style, or ``None`` if cancelled."""
        wx = self._wx
        try:
            if self._show_modal_dialog is not None:
                result = self._show_modal_dialog(self._dialog, "Caption Settings")
            else:
                result = self._dialog.ShowModal()  # dialog_button_contract: exempt
            if result != wx.ID_OK:
                return None
            style = self.chosen()
            self._announce(describe(style))
            return style
        finally:
            self._dialog.Destroy()


def _index_of(values: Any, wanted: Any) -> int:
    """Where *wanted* sits in *values*, or 0. Never raises on a stored oddity."""
    try:
        return list(values).index(wanted)
    except ValueError:
        return 0
