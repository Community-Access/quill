"""The Audio / DSP page: equalizer, boost, normalize, skip-silence (PRD 7.4-7.6).

A self-contained ``wx.Panel`` so the media player frame stays under its size
budget and the same panel can be reused by the in-QUILL player later. It exposes
:meth:`settings` (the current :class:`~quill.core.media.DspSettings`) and calls
an injected ``on_change`` whenever the user adjusts anything, so the host can
compile filters via :func:`quill.core.media.build_audio_filters` and apply them.

Accessibility: each of the ten band sliders is a labelled ``wx.Slider`` whose
value **is** the gain in dB (range -12..+12), so a screen reader speaks a
meaningful number; presets and toggles carry explicit accessible names.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.media import EQ_BANDS_HZ, EQ_PRESETS, DspSettings, Equalizer
from quill.ui.accessible_names import set_accessible_name

_EQ_KEYS = ("flat", "voice", "bass", "treble", "night", "podcast")
_BOOST_VALUES = (0, 3, 6)


class AudioDspPanel(wx.Panel):
    """Equalizer + effects controls, reporting changes through ``on_change``."""

    def __init__(self, parent: wx.Window, *, on_change: Callable[[DspSettings], None]) -> None:
        super().__init__(parent)
        self.SetName("Audio")
        self._on_change = on_change

        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self, label="&Equalizer preset:"), 0, wx.ALL, 6)
        self._preset = wx.Choice(self, choices=[key.capitalize() for key in _EQ_KEYS])
        self._preset.SetSelection(0)
        set_accessible_name(self._preset, "Equalizer preset")
        self._preset.SetHelpText(
            "A ready-made shape for the ten band sliders below -- Flat, "
            "Voice, Bass, Treble, Night, or Podcast. Choosing one overwrites "
            "the sliders; adjust any slider afterwards to fine-tune. Flat is "
            "the default and changes nothing."
        )
        self._preset.Bind(wx.EVT_CHOICE, self._on_preset)
        root.Add(self._preset, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # Ten band sliders; the slider value is the gain in dB.
        bands = wx.FlexGridSizer(rows=len(EQ_BANDS_HZ), cols=2, vgap=2, hgap=8)
        bands.AddGrowableCol(1, 1)
        self._band_sliders: list[wx.Slider] = []
        for hz in EQ_BANDS_HZ:
            label = f"{hz} Hz" if hz < 1000 else f"{hz // 1000} kHz"
            bands.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            slider = wx.Slider(self, value=0, minValue=-12, maxValue=12, style=wx.SL_HORIZONTAL)
            set_accessible_name(slider, f"{label} gain in decibels")
            slider.SetHelpText(
                f"How much to raise or cut the {label} band, in decibels, "
                "from -12 to +12. Zero leaves the band unchanged. Takes "
                "effect as you move it; audio effects need the libmpv "
                "engine."
            )
            slider.Bind(wx.EVT_SLIDER, self._fire)
            bands.Add(slider, 1, wx.EXPAND)
            self._band_sliders.append(slider)
        root.Add(bands, 0, wx.EXPAND | wx.ALL, 6)

        root.Add(wx.StaticText(self, label="Volume &boost:"), 0, wx.ALL, 6)
        self._boost = wx.Choice(self, choices=["Off", "+3 dB", "+6 dB"])
        self._boost.SetSelection(0)
        set_accessible_name(self._boost, "Volume boost")
        self._boost.SetHelpText(
            "Extra gain on top of the volume control, for a quiet recording: "
            "Off, +3 dB, or +6 dB. Off is the default. Like the equalizer, "
            "it needs the libmpv engine."
        )
        self._boost.Bind(wx.EVT_CHOICE, self._fire)
        root.Add(self._boost, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self._normalize = wx.CheckBox(self, label="&Normalize loudness")
        self._skip_silence = wx.CheckBox(self, label="Skip &silence")
        for check in (self._normalize, self._skip_silence):
            check.Bind(wx.EVT_CHECKBOX, self._fire)
            root.Add(check, 0, wx.ALL, 6)

        self.SetSizer(root)

    def settings(self) -> DspSettings:
        """The current DSP settings from the live controls."""
        gains = tuple(float(slider.GetValue()) for slider in self._band_sliders)
        return DspSettings(
            equalizer=Equalizer(gains=gains, name="custom"),
            boost_db=float(_BOOST_VALUES[max(0, self._boost.GetSelection())]),
            normalize=self._normalize.GetValue(),
            skip_silence=self._skip_silence.GetValue(),
        )

    def _on_preset(self, _event: wx.CommandEvent) -> None:
        key = _EQ_KEYS[max(0, self._preset.GetSelection())]
        for slider, gain in zip(self._band_sliders, EQ_PRESETS[key], strict=False):
            slider.SetValue(int(gain))
        self._fire()

    def _fire(self, _event: wx.CommandEvent | None = None) -> None:
        self._on_change(self.settings())


__all__ = ["AudioDspPanel"]
