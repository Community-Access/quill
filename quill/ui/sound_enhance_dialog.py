"""Playback > Sound Enhancements... -- a three-band EQ (Bass/Mid/Treble
sliders), a compressor, (podcasts only) Smart Speed, and (radio) the
listener-level sound options: mono downmix and night mode.

Shared by Radio and Podcasts (both standalone apps and MainFrame). Sliders,
not a single named preset: the Quick Preset combo box is a shortcut that sets
all three sliders at once (Flat / Bass Boost / Voice Clarity / Podcast, from
``core/audio_enhance.EQ_PRESETS``) -- moving any slider away from a preset's
exact values flips the combo to "Custom", which is a status readout, not a
selectable target of its own. All apply through the host player controller's
``set_enhancement`` (see ``core/audio_enhance.py`` for why -- ffmpeg relay,
no new audio backend, no live per-drag-tick preview: the relay can only be
restarted, not tweaked in place, so changes take effect on Apply, not on
every slider movement). Turning anything on reconnects what's currently
playing through the filtered relay. Smart Speed (silence trimming) only
makes sense for bounded, spoken-word content -- ``show_smart_speed`` gates
whether that checkbox exists at all (Radio never passes it; a hidden-but-
present control would be a worse screen-reader experience than one that
simply isn't there).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.audio_enhance import EQ_BAND_MAX_DB, EQ_BAND_MIN_DB, EQ_PRESETS
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_PRESET_NAMES = ("Custom", *EQ_PRESETS)


class SoundEnhanceDialog:
    """Returns ``(bass_db, mid_db, treble_db, compressor_enabled,
    smart_speed_enabled)``, or ``None`` on Cancel. ``smart_speed_enabled`` is
    always ``False`` when ``show_smart_speed`` is ``False`` (there is no
    control to read it from)."""

    def __init__(
        self,
        parent: object,
        *,
        bass_db: float,
        mid_db: float,
        treble_db: float,
        compressor_enabled: bool,
        subject: str = "station",
        show_smart_speed: bool = False,
        smart_speed_enabled: bool = False,
        show_sound_options: bool = False,
        mono_enabled: bool = False,
        night_mode_enabled: bool = False,
        announce_cb: Callable[[str], None] | None = None,
        on_reset: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._show_smart_speed = show_smart_speed
        self._on_reset = on_reset
        self._result: tuple[float, float, float, bool, bool] | None = None
        self._sound_options: tuple[bool, bool] = (mono_enabled, night_mode_enabled)
        # wx.Window.SetName() is inert for MSAA/UIA on Windows (see
        # quill.ui.accessible_names) -- screen readers there normally infer a
        # name from the adjacent wx.StaticText instead, but that inference
        # does not cover wx.Slider/Trackbar, so the band sliders read with no
        # name at all. SetAccessible() with a GetName override is the same
        # fix already used for table_studio_accessible.ListGridAccessible.
        try:
            _acc_ok = wx.ACC_OK

            class _SliderAccessible(wx.Accessible):  # type: ignore[misc]
                def __init__(self, window: object, name: str) -> None:
                    super().__init__(window)
                    self._name = name

                def GetName(self, child_id: int) -> tuple[int, str]:
                    return _acc_ok, self._name

            self._slider_accessible_cls: type | None = _SliderAccessible
        except Exception:
            self._slider_accessible_cls = None

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
        grid.Add(wx.StaticText(self.dialog, label="&Quick preset:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._preset_choice = wx.Choice(self.dialog, choices=list(_PRESET_NAMES))
        self._preset_choice.SetName("Quick preset -- sets all three sliders at once")
        grid.Add(self._preset_choice, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._bass_slider = self._add_band_slider(root, "&Bass", bass_db)
        self._mid_slider = self._add_band_slider(root, "&Mid", mid_db)
        self._treble_slider = self._add_band_slider(root, "&Treble", treble_db)
        self._sync_preset_choice()
        self._preset_choice.Bind(wx.EVT_CHOICE, self._on_preset_choice)
        for slider in (self._bass_slider, self._mid_slider, self._treble_slider):
            slider.Bind(wx.EVT_SLIDER, self._on_slider_changed)

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

        # Listener-level sound options (radio: shared, not per-station --
        # they describe the listener's ears and situation, not a station).
        self._mono_check: wx.CheckBox | None = None
        self._night_mode_check: wx.CheckBox | None = None
        if show_sound_options:
            self._mono_check = wx.CheckBox(self.dialog, label="Com&bine channels into mono")
            self._mono_check.SetName(
                "Combine channels into mono -- both stereo channels blended into "
                "one, so nothing is lost with single-sided hearing or one earbud"
            )
            self._mono_check.SetValue(mono_enabled)
            root.Add(self._mono_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            self._night_mode_check = wx.CheckBox(self.dialog, label="&Night mode (even loudness)")
            self._night_mode_check.SetName(
                "Night mode -- automatically lifts quiet passages toward a "
                "consistent loudness, for low-volume listening"
            )
            self._night_mode_check.SetValue(night_mode_enabled)
            root.Add(self._night_mode_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._reset_btn: wx.Button | None = None
        if on_reset is not None:
            self._reset_btn = wx.Button(self.dialog, label="&Reset to Default")
            self._reset_btn.SetName(
                "Reset to Default -- stop overriding this station, follow the shared default"
            )
            buttons.Add(self._reset_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&Apply")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        ok_btn.Bind(wx.EVT_BUTTON, self._on_apply)
        if self._reset_btn is not None:
            self._reset_btn.Bind(wx.EVT_BUTTON, self._on_reset_click)

    def _add_band_slider(self, root: object, label: str, value_db: float):
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        text = label.replace("&", "")
        row.Add(wx.StaticText(self.dialog, label=f"{label}:"), 0, wx.ALIGN_CENTER_VERTICAL)
        slider = wx.Slider(
            self.dialog,
            value=round(max(EQ_BAND_MIN_DB, min(EQ_BAND_MAX_DB, value_db))),
            minValue=int(EQ_BAND_MIN_DB),
            maxValue=int(EQ_BAND_MAX_DB),
            style=wx.SL_HORIZONTAL | wx.SL_LABELS,
        )
        slider.SetName(f"{text}, decibels, {int(EQ_BAND_MIN_DB)} to {int(EQ_BAND_MAX_DB)}")
        if self._slider_accessible_cls is not None:
            try:
                slider.SetAccessible(self._slider_accessible_cls(slider, slider.GetName()))
            except Exception:
                pass
        row.Add(slider, 1, wx.EXPAND | wx.LEFT, 8)
        root.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        return slider

    def _current_band_values(self) -> tuple[float, float, float]:
        return (
            float(self._bass_slider.GetValue()),
            float(self._mid_slider.GetValue()),
            float(self._treble_slider.GetValue()),
        )

    def _sync_preset_choice(self) -> None:
        values = self._current_band_values()
        for name, preset_values in EQ_PRESETS.items():
            if preset_values == values:
                self._preset_choice.SetSelection(_PRESET_NAMES.index(name))
                return
        self._preset_choice.SetSelection(0)  # "Custom"

    def _on_slider_changed(self, _event: object) -> None:
        self._sync_preset_choice()

    def _on_preset_choice(self, _event: object) -> None:
        index = self._preset_choice.GetSelection()
        if index <= 0 or index >= len(_PRESET_NAMES):
            return  # "Custom" is a status readout, not a settable target
        name = _PRESET_NAMES[index]
        bass, mid, treble = EQ_PRESETS[name]
        self._bass_slider.SetValue(round(bass))
        self._mid_slider.SetValue(round(mid))
        self._treble_slider.SetValue(round(treble))
        self._announce(f"{name}: Bass {bass:+.0f}, Mid {mid:+.0f}, Treble {treble:+.0f}")

    def show(self) -> tuple[float, float, float, bool, bool] | None:
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

    def _on_reset_click(self, _event: object) -> None:
        if self._on_reset is not None:
            self._on_reset()
        self.dialog.EndModal(self._wx.ID_CANCEL)

    @property
    def sound_options(self) -> tuple[bool, bool]:
        """(mono_enabled, night_mode_enabled) as applied -- only meaningful
        after an OK ``show`` with ``show_sound_options=True``. A separate
        property (not part of the ``show`` tuple) so existing callers'
        5-tuple contract is untouched."""
        return self._sound_options

    def _on_apply(self, _event: object) -> None:
        bass, mid, treble = self._current_band_values()
        smart_speed = self._smart_speed_check.GetValue() if self._smart_speed_check else False
        self._result = (bass, mid, treble, self._compressor_check.GetValue(), smart_speed)
        self._sound_options = (
            bool(self._mono_check.GetValue()) if self._mono_check else False,
            bool(self._night_mode_check.GetValue()) if self._night_mode_check else False,
        )
        self.dialog.EndModal(self._wx.ID_OK)
