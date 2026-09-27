"""View > Advanced Options: the encoder settings, in the main window.

Until 2026-09-27 these lived behind an **Advanced...** button that opened the
Audio Studio's whole Convert Audio dialog -- a second window with its own
queue, its own format list and its own Convert button, which ran a different
conversion from the one the main window was set up for. Two places to set up
one job is one too many to keep in your head, and a checkbox inside a dialog
that reveals more of that dialog is a thing you have to discover by tabbing.

So the settings moved into the main window, hidden until **View > Advanced
Options** (Ctrl+Alt+V) is checked -- the Windows way to show more of a window
-- and they shape the same Convert as everything else on the page. Each
starts on its neutral choice ("use the preset"), so showing them changes
nothing until you change one; the choices are remembered with the rest.

The choice tables are the ones the Convert Audio dialog already uses
(:mod:`quill.ui.audio_studio.convert_audio_dialog`), so both surfaces offer
the same values in the same words.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.audio import exact_optilab as exact_optilab_component
from quill.core.audio.convert import Channels, ConversionSpec, OnExisting
from quill.core.audio.exact_optilab import ExactOptilab
from quill.ui.accessible_names import set_accessible_name
from quill.ui.audio_studio.convert_audio_dialog import (
    _BITRATE_CHOICES,
    _CHANNEL_CHOICES,
    _CONFLICT_CHOICES,
    _DEPTH_CHOICES,
    _EXACT_OPTILAB_CHOICES,
    _RATE_CHOICES,
    apply_advanced,
)

#: (settings field, label, table, F1 sentence), in the order they appear.
_ROWS: tuple[tuple[str, str, tuple[tuple[Any, str], ...], str], ...] = (
    (
        "adv_bitrate",
        "Bit rate (si&ze and quality):",
        _BITRATE_CHOICES,
        "The bit rate for compressed formats, 96 to 320 kbps. Use preset (the "
        "default) keeps what the preset says. Lossless formats ignore it.",
    ),
    (
        "adv_rate",
        "Sa&mple rate:",
        _RATE_CHOICES,
        "Resample every file to this rate. The default keeps each file's own. A "
        "format that cannot take the rate you choose gets the nearest it can.",
    ),
    (
        "adv_channels",
        "Cha&nnels:",
        _CHANNEL_CHOICES,
        "Mono or stereo. The default keeps each file's own; mono halves the size of speech.",
    ),
    (
        "adv_depth",
        "Bit depth:",
        _DEPTH_CHOICES,
        "16, 24 or 32-bit float for WAV, AIFF, FLAC and the other lossless "
        "formats. The default keeps each file's own. Compressed formats ignore it.",
    ),
    (
        "on_existing",
        "If a file already e&xists:",
        _CONFLICT_CHOICES,
        "What to do when a converted file would have the name of one already in "
        "the output folder: number the new one (the default, which never "
        "destroys anything), skip it, or replace it.",
    ),
    (
        "adv_polish",
        "Broadcast pol&ish:",
        _EXACT_OPTILAB_CHOICES,
        "Runs each converted file through the OptiLab Core processing engine: "
        "Podcast Leveler for speech, Stream Polish for music, Smooth Limiter for "
        "peaks. Off by default; unavailable when this build does not include it.",
    ),
)


def build(host: Any, panel: wx.Window) -> wx.BoxSizer:
    """Create the hidden Advanced section on *panel*; controls land on *host*."""
    box = wx.BoxSizer(wx.VERTICAL)
    host._advanced_choices = {}
    settings = host._settings
    for field_name, label, table, help_text in _ROWS:
        box.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        ctrl = wx.Choice(panel, choices=[text for _value, text in table])
        values = [str(value) for value, _text in table]
        saved = str(getattr(settings, field_name, ""))
        ctrl.SetSelection(values.index(saved) if saved in values else 0)
        set_accessible_name(ctrl, label)
        ctrl.SetHelpText(help_text)
        ctrl.Bind(wx.EVT_CHOICE, host._on_choice_changed)
        box.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        host._advanced_choices[field_name] = (ctrl, table)
    if not exact_optilab_component.available():
        host._advanced_choices["adv_polish"][0].Enable(False)
    host._recurse = wx.CheckBox(panel, label="Look in subfolders too")
    host._recurse.SetValue(bool(settings.recurse))
    set_accessible_name(host._recurse, "Look in subfolders too")
    host._recurse.SetHelpText(
        "When a folder is in the queue, convert the files in its subfolders as "
        "well, and rebuild the same folder layout in the output folder. On by "
        "default."
    )
    host._recurse.Bind(wx.EVT_CHECKBOX, host._on_choice_changed)
    box.Add(host._recurse, 0, wx.ALL, 8)
    return box


def value(host: Any, field_name: str) -> Any:
    """The value behind one Advanced choice (index 0 is the neutral choice)."""
    ctrl, table = host._advanced_choices[field_name]
    return table[max(0, ctrl.GetSelection())][0]


def remember(host: Any) -> None:
    """Copy the Advanced choices onto the host's settings (as plain strings)."""
    for field_name in host._advanced_choices:
        setattr(host._settings, field_name, str(value(host, field_name)))
    host._settings.recurse = bool(host._recurse.GetValue())


def apply(host: Any, spec: ConversionSpec) -> ConversionSpec:
    """Layer the Advanced choices onto *spec*; neutral choices change nothing."""
    bitrate, rate = value(host, "adv_bitrate"), value(host, "adv_rate")
    channels, depth = value(host, "adv_channels"), value(host, "adv_depth")
    polish = value(host, "adv_polish")
    return apply_advanced(
        spec,
        bitrate_kbps=int(bitrate) if bitrate else None,
        sample_rate=int(rate) if rate else None,
        channels=channels if channels is not Channels.KEEP else None,
        bit_depth=int(depth) if depth else None,
        exact_optilab=ExactOptilab(mode=polish) if polish else None,
    )


def on_existing(host: Any) -> OnExisting:
    return OnExisting(value(host, "on_existing"))


def show(host: Any, visible: bool) -> None:
    """Show or hide the section; showing moves focus to its first choice."""
    host._main_sizer.Show(host._advanced_box, visible, recursive=True)
    host._main_panel.Layout()
    host._settings.show_advanced = bool(visible)
    if visible:
        host._advanced_choices["adv_bitrate"][0].SetFocus()
