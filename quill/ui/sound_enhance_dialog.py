"""Playback > Sound Enhancements... -- an EQ preset, a compressor, and
(podcasts only) Smart Speed.

Shared by Radio and Podcasts (both standalone apps and MainFrame). Deliberately
not raw dB sliders per band: one named preset (Flat / Bass Boost / Voice
Clarity / Podcast) in a combo box, plus a single "Even Out Volume" checkbox
for the compressor. All apply through the host player controller's
``set_enhancement`` (see ``core/audio_enhance.py`` for why -- ffmpeg relay,
no new audio backend). Turning anything on reconnects what's currently
playing through the filtered relay. Smart Speed (silence trimming) only
makes sense for bounded, spoken-word content -- ``show_smart_speed`` gates
whether that checkbox exists at all (Radio never passes it; a hidden-but-
present control would be a worse screen-reader experience than one that
simply isn't there).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.audio_enhance import DEFAULT_EQ_PRESET, EQ_PRESETS
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_PRESET_NAMES = tuple(EQ_PRESETS)


class SoundEnhanceDialog:
    """Returns ``(eq_preset, compressor_enabled, smart_speed_enabled)``, or
    ``None`` on Cancel. ``smart_speed_enabled`` is always ``False`` when
    ``show_smart_speed`` is ``False`` (there is no control to read it from)."""

    def __init__(
        self,
        parent: object,
        *,
        eq_preset: str,
        compressor_enabled: bool,
        subject: str = "station",
        show_smart_speed: bool = False,
        smart_speed_enabled: bool = False,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._show_smart_speed = show_smart_speed
        self._result: tuple[str, bool, bool] | None = None

        self.dialog = wx.Dialog(parent, title="Sound Enhancements")
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                f"Optional processing applied to whatever {subject} is playing. "
                "Needs FFmpeg (Help > Get FFmpeg...)."
            ),
        )
        intro.Wrap(420)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(
            wx.StaticText(self.dialog, label="&Equalizer preset:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._preset_choice = wx.Choice(self.dialog, choices=list(_PRESET_NAMES))
        self._preset_choice.SetName("Equalizer preset")
        preset = eq_preset if eq_preset in _PRESET_NAMES else DEFAULT_EQ_PRESET
        self._preset_choice.SetSelection(_PRESET_NAMES.index(preset))
        grid.Add(self._preset_choice, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._compressor_check = wx.CheckBox(self.dialog, label="&Even Out Volume")
        self._compressor_check.SetName(
            "Even out volume -- boosts quiet passages and tames loud ones"
        )
        self._compressor_check.SetValue(compressor_enabled)
        root.Add(self._compressor_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._smart_speed_check: wx.CheckBox | None = None
        if show_smart_speed:
            self._smart_speed_check = wx.CheckBox(self.dialog, label="&Smart Speed")
            self._smart_speed_check.SetName(
                "Smart Speed -- trims silence between words and sentences"
            )
            self._smart_speed_check.SetValue(smart_speed_enabled)
            root.Add(self._smart_speed_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&Apply")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        ok_btn.Bind(wx.EVT_BUTTON, self._on_apply)

    def show(self) -> tuple[str, bool, bool] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Apply",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, "Sound Enhancements", announce=self._announce)
            return self._result if answer == wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_apply(self, _event: object) -> None:
        index = self._preset_choice.GetSelection()
        preset = _PRESET_NAMES[index] if 0 <= index < len(_PRESET_NAMES) else DEFAULT_EQ_PRESET
        smart_speed = self._smart_speed_check.GetValue() if self._smart_speed_check else False
        self._result = (preset, self._compressor_check.GetValue(), smart_speed)
        self.dialog.EndModal(self._wx.ID_OK)
