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
restarted, not tweaked in place, so changes take effect on OK, not on
every slider movement; the mpv engine applies the same graph live with no
reconnect at all). Turning anything on makes what's currently playing
heard through the new settings. Smart Speed (silence trimming) only
makes sense for bounded, spoken-word content -- ``show_smart_speed`` gates
whether that checkbox exists at all (Radio never passes it; a hidden-but-
present control would be a worse screen-reader experience than one that
simply isn't there).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

from quill.core.audio_enhance import (
    EQ_BAND_MAX_DB,
    EQ_BAND_MIN_DB,
    EQ_PRESETS,
    OPTILAB_INPUT_MAX_DB,
    OPTILAB_INPUT_MIN_DB,
    OPTILAB_MODE_LABELS,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_PRESET_NAMES = ("Custom", *EQ_PRESETS)

#: Channel-mode RadioBox order -- index maps to the stored ``channel_mode``.
_CHANNEL_ORDER = ("stereo", "mono", "left", "right")

#: OptiLab mode Choice order -- index maps to the stored ``optilab_mode``.
_OPTILAB_ORDER = ("off", "podcast", "stream", "limiter")


class SoundOptions(NamedTuple):
    """The listener-level options the dialog returns via :attr:`sound_options`
    (channel mode, night mode, and OptiLab broadcast polish)."""

    channel_mode: str = "stereo"
    night_mode_enabled: bool = False
    optilab_enabled: bool = False
    optilab_mode: str = "off"
    optilab_input_db: float = 0.0
    optilab_auto_adapt: int = 0


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
        channel_mode: str = "stereo",
        night_mode_enabled: bool = False,
        optilab_enabled: bool = False,
        optilab_mode: str = "off",
        optilab_input_db: float = 0.0,
        optilab_auto_adapt: int = 0,
        announce_cb: Callable[[str], None] | None = None,
        on_reset: Callable[[], None] | None = None,
        on_live_change: Callable[[object], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._show_smart_speed = show_smart_speed
        self._on_reset = on_reset
        # Live preview: apply changes to what's playing as controls move, so the
        # listener hears them without pressing OK. Cancel reverts to how it was.
        self._on_live_change = on_live_change
        self._previewed = False
        self._did_reset = False
        self._result: tuple[float, float, float, bool, bool] | None = None
        self._sound_options = SoundOptions(
            channel_mode=channel_mode,
            night_mode_enabled=night_mode_enabled,
            optilab_enabled=optilab_enabled,
            optilab_mode=optilab_mode,
            optilab_input_db=optilab_input_db,
            optilab_auto_adapt=optilab_auto_adapt,
        )
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
        self._channel_radio: wx.RadioBox | None = None
        self._night_mode_check: wx.CheckBox | None = None
        self._optilab_check: wx.CheckBox | None = None
        self._optilab_mode_choice: wx.Choice | None = None
        self._optilab_input_ctrl: wx.SpinCtrl | None = None
        self._optilab_adapt_slider: wx.Slider | None = None
        if show_sound_options:
            # A RadioBox (not a checkbox): Stereo / Mono / Left only / Right only.
            # Left/Right send just that channel to both ears, so the radio can
            # play in one ear while a screen reader uses the other. Self-labeling
            # and arrow-selectable, so no SetName inference workaround is needed.
            self._channel_radio = wx.RadioBox(
                self.dialog,
                label="C&hannel mode",
                choices=["Stereo", "Mono", "Left only", "Right only"],
                majorDimension=1,
                style=wx.RA_SPECIFY_COLS,
            )
            self._channel_radio.SetSelection(
                _CHANNEL_ORDER.index(channel_mode) if channel_mode in _CHANNEL_ORDER else 0
            )
            root.Add(self._channel_radio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            self._night_mode_check = wx.CheckBox(self.dialog, label="&Night mode (even loudness)")
            self._night_mode_check.SetName(
                "Night mode -- automatically lifts quiet passages toward a "
                "consistent loudness, for low-volume listening"
            )
            self._night_mode_check.SetValue(night_mode_enabled)
            root.Add(self._night_mode_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

            # OptiLab broadcast polish (adapted from OptiLab Core by dgl1984,
            # Apache-2.0). A bypass checkbox so the chosen mode is remembered
            # while turned off, a Mode choice, an Input trim (0 dB by default),
            # and an Auto-Adapt amount.
            optilab_box = wx.StaticBoxSizer(
                wx.VERTICAL, self.dialog, "Broadcast polish (OptiLab)"
            )
            self._optilab_check = wx.CheckBox(
                self.dialog, label="&Apply broadcast polish (OptiLab)"
            )
            self._optilab_check.SetName(
                "Apply broadcast polish -- a one-touch leveling, density, and "
                "limiting chain adapted from OptiLab by dgl1984. Uncheck to bypass "
                "it while keeping your chosen mode"
            )
            self._optilab_check.SetValue(optilab_enabled)
            optilab_box.Add(self._optilab_check, 0, wx.ALL, 6)

            mode_row = wx.BoxSizer(wx.HORIZONTAL)
            mode_row.Add(
                wx.StaticText(self.dialog, label="&Polish mode:"), 0, wx.ALIGN_CENTER_VERTICAL
            )
            self._optilab_mode_choice = wx.Choice(
                self.dialog, choices=[OPTILAB_MODE_LABELS[m] for m in _OPTILAB_ORDER]
            )
            self._optilab_mode_choice.SetName(
                "Broadcast polish mode -- Podcast Leveler for speech, Stream Polish "
                "for music, Smooth Limiter for clean peak control"
            )
            self._optilab_mode_choice.SetSelection(
                _OPTILAB_ORDER.index(optilab_mode) if optilab_mode in _OPTILAB_ORDER else 0
            )
            mode_row.Add(self._optilab_mode_choice, 1, wx.EXPAND | wx.LEFT, 8)
            optilab_box.Add(mode_row, 0, wx.EXPAND | wx.ALL, 6)

            input_row = wx.BoxSizer(wx.HORIZONTAL)
            input_row.Add(
                wx.StaticText(self.dialog, label="&Input (dB):"), 0, wx.ALIGN_CENTER_VERTICAL
            )
            self._optilab_input_ctrl = wx.SpinCtrl(
                self.dialog,
                min=int(OPTILAB_INPUT_MIN_DB),
                max=int(OPTILAB_INPUT_MAX_DB),
                initial=int(round(optilab_input_db)),
            )
            self._optilab_input_ctrl.SetName(
                "Input level in decibels for broadcast polish; zero leaves the level "
                "unchanged"
            )
            input_row.Add(self._optilab_input_ctrl, 0, wx.LEFT, 8)
            optilab_box.Add(input_row, 0, wx.EXPAND | wx.ALL, 6)

            adapt_row = wx.BoxSizer(wx.HORIZONTAL)
            adapt_row.Add(
                wx.StaticText(self.dialog, label="A&uto-Adapt:"), 0, wx.ALIGN_CENTER_VERTICAL
            )
            self._optilab_adapt_slider = wx.Slider(
                self.dialog,
                value=max(0, min(100, int(optilab_auto_adapt))),
                minValue=0,
                maxValue=100,
                style=wx.SL_HORIZONTAL | wx.SL_LABELS,
            )
            self._optilab_adapt_slider.SetName(
                "Auto-Adapt, percent, 0 to 100 -- higher leans the leveling and "
                "density more assertive"
            )
            if self._slider_accessible_cls is not None:
                try:
                    self._optilab_adapt_slider.SetAccessible(
                        self._slider_accessible_cls(
                            self._optilab_adapt_slider, self._optilab_adapt_slider.GetName()
                        )
                    )
                except Exception:  # noqa: BLE001 - accessible name is best-effort
                    pass
            adapt_row.Add(self._optilab_adapt_slider, 1, wx.EXPAND | wx.LEFT, 8)
            optilab_box.Add(adapt_row, 0, wx.EXPAND | wx.ALL, 6)

            root.Add(optilab_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._reset_btn: wx.Button | None = None
        if on_reset is not None:
            self._reset_btn = wx.Button(self.dialog, label="&Reset to Default")
            self._reset_btn.SetName(
                "Reset to Default -- stop overriding this station, follow the shared default"
            )
            buttons.Add(self._reset_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&OK")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        ok_btn.Bind(wx.EVT_BUTTON, self._on_apply)
        if self._reset_btn is not None:
            self._reset_btn.Bind(wx.EVT_BUTTON, self._on_reset_click)

        # Live preview: a short debounce so a slider drag through several values
        # only applies once it settles (one wx reconnect, imperceptible on mpv).
        # Every value-changing control schedules it.
        self._live_timer = wx.Timer(self.dialog)
        self.dialog.Bind(wx.EVT_TIMER, lambda _e: self._emit_live_preview(), self._live_timer)
        if self._on_live_change is not None:
            # EQ sliders and the preset choice already have handlers
            # (_on_slider_changed / _on_preset_choice) that now also schedule a
            # preview; bind the remaining controls here.
            self._compressor_check.Bind(wx.EVT_CHECKBOX, self._on_control_changed)
            if self._smart_speed_check is not None:
                self._smart_speed_check.Bind(wx.EVT_CHECKBOX, self._on_control_changed)
            if self._channel_radio is not None:
                self._channel_radio.Bind(wx.EVT_RADIOBOX, self._on_control_changed)
            if self._night_mode_check is not None:
                self._night_mode_check.Bind(wx.EVT_CHECKBOX, self._on_control_changed)
            if self._optilab_check is not None:
                self._optilab_check.Bind(wx.EVT_CHECKBOX, self._on_control_changed)
            if self._optilab_mode_choice is not None:
                self._optilab_mode_choice.Bind(wx.EVT_CHOICE, self._on_control_changed)
            if self._optilab_input_ctrl is not None:
                self._optilab_input_ctrl.Bind(wx.EVT_SPINCTRL, self._on_control_changed)
            if self._optilab_adapt_slider is not None:
                self._optilab_adapt_slider.Bind(wx.EVT_SLIDER, self._on_control_changed)

        # The starting values, so Cancel can revert a live preview to how it was.
        self._original_snapshot = self._live_snapshot()

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
        self._schedule_live_preview()

    def _on_control_changed(self, _event: object) -> None:
        """Any non-slider control changed -- schedule a live preview."""
        self._schedule_live_preview()

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
        self._schedule_live_preview()

    def _read_sound_options(self) -> SoundOptions:
        """The listener-level options from the live controls."""
        return SoundOptions(
            channel_mode=(
                _CHANNEL_ORDER[self._channel_radio.GetSelection()]
                if self._channel_radio
                else "stereo"
            ),
            night_mode_enabled=(
                bool(self._night_mode_check.GetValue()) if self._night_mode_check else False
            ),
            optilab_enabled=(
                bool(self._optilab_check.GetValue()) if self._optilab_check else False
            ),
            optilab_mode=(
                _OPTILAB_ORDER[self._optilab_mode_choice.GetSelection()]
                if self._optilab_mode_choice
                else "off"
            ),
            optilab_input_db=(
                float(self._optilab_input_ctrl.GetValue()) if self._optilab_input_ctrl else 0.0
            ),
            optilab_auto_adapt=(
                int(self._optilab_adapt_slider.GetValue()) if self._optilab_adapt_slider else 0
            ),
        )

    def _live_snapshot(self) -> tuple[float, float, float, bool, bool, SoundOptions]:
        """Everything the live-preview / revert callback needs: the EQ bands,
        the compressor, Smart Speed, and the listener-level options."""
        bass, mid, treble = self._current_band_values()
        smart_speed = self._smart_speed_check.GetValue() if self._smart_speed_check else False
        return (bass, mid, treble, self._compressor_check.GetValue(), smart_speed,
                self._read_sound_options())

    def _schedule_live_preview(self) -> None:
        if self._on_live_change is None:
            return
        # Restart the one-shot debounce; the last change in a drag wins.
        self._live_timer.Start(180, oneShot=True)

    def _emit_live_preview(self) -> None:
        if self._on_live_change is None:
            return
        self._previewed = True
        try:
            self._on_live_change(self._live_snapshot())
        except Exception:  # noqa: BLE001 - a preview must never crash the dialog
            pass

    def show(self) -> tuple[float, float, float, bool, bool] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="OK",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, "Sound Enhancements", announce=self._announce)
        finally:
            try:
                self._live_timer.Stop()
            except Exception:  # noqa: BLE001 - stopping a timer must never raise
                pass
            self.dialog.Destroy()
        if answer == wx.ID_OK:
            return self._result
        # Cancel/Escape/X: revert a live preview to how it was -- unless Reset
        # already restored the shared default (its own live update stands).
        if self._on_live_change is not None and self._previewed and not self._did_reset:
            try:
                self._on_live_change(self._original_snapshot)
            except Exception:  # noqa: BLE001 - revert must never raise
                pass
        return None

    def _on_reset_click(self, _event: object) -> None:
        self._did_reset = True
        if self._on_reset is not None:
            self._on_reset()
        self.dialog.EndModal(self._wx.ID_CANCEL)

    @property
    def sound_options(self) -> SoundOptions:
        """The listener-level options as applied (channel mode, night mode, and
        OptiLab broadcast polish) -- only meaningful after an OK ``show`` with
        ``show_sound_options=True``. A separate property (not part of the
        ``show`` tuple) so existing callers' 5-tuple contract is untouched."""
        return self._sound_options

    def _on_apply(self, _event: object) -> None:
        bass, mid, treble = self._current_band_values()
        smart_speed = self._smart_speed_check.GetValue() if self._smart_speed_check else False
        self._result = (bass, mid, treble, self._compressor_check.GetValue(), smart_speed)
        self._sound_options = self._read_sound_options()
        self.dialog.EndModal(self._wx.ID_OK)
