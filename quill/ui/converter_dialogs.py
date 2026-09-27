"""Quill Converter's own two windows: Custom Effects, and a read-only report.

**Custom Effects** is the whole processing catalogue on one page: every
switch a named recipe can turn on, the loudness target, gain, speed, fades,
and "keep only part of each file". It opens seeded with whatever the main
window's Effects choice currently means, so choosing "Podcast ready" and then
Custom Effects shows exactly what that recipe does and lets you change one
thing. OK makes the result the Custom recipe.

**The report window** is one read-only text box and a Copy button. File
Properties, the Conversion Report and the Keyboard Shortcuts list all use it,
because a multi-line read-only edit is the one surface every screen reader
reviews line by line, word by word and character by character without any
special mode -- the right home for facts somebody may want to read twice or
paste into an email to support.

Access keys are unique within each window (GATE-14); OK, Cancel and Close
carry none. Every control has its F1 sentence inline (GATE-CONVERTER-HELP).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

import wx

from quill.core.audio.dsp import DspOptions, loudness_choices
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

EFFECTS_TITLE = "Custom Effects"

#: (DspOptions field, checkbox label, F1 sentence), in the order they apply.
_SWITCHES: tuple[tuple[str, str, str], ...] = (
    (
        "high_pass",
        "Remove low &rumble",
        "Cuts the rumble below 30 Hz -- traffic, "
        "handling noise, air conditioning -- that you feel more than hear.",
    ),
    (
        "remove_hum",
        "Remove electrical &hum",
        "Notches out the 50 and 60 Hz mains hum "
        "a ground loop or a cheap cable adds, and its first harmonic.",
    ),
    (
        "noise_reduction",
        "Reduce background &noise",
        "Takes down steady hiss and fan "
        "noise. Strong settings can make a voice sound watery, so this is gentle.",
    ),
    (
        "trim_silence",
        "Remove long &silences",
        "Cuts every pause longer than half a second, anywhere in the file.",
    ),
    (
        "deesser",
        "D&e-ess (soften harsh s sounds)",
        "Softens the sharp s and sh sounds that a close microphone exaggerates.",
    ),
    (
        "voice_clarity",
        "&Voice clarity",
        "Lifts the frequencies that carry consonants "
        "and trims muddiness -- easier to follow, and kinder to hearing aids.",
    ),
    ("bass_boost", "&Bass boost", "Adds six decibels of warmth below 100 Hz."),
    ("treble_boost", "&Treble boost", "Adds brightness above 4 kHz."),
    (
        "dialogue_boost",
        "&Dialogue boost (films and TV)",
        "Brings speech forward over music and effects. The result is stereo.",
    ),
    (
        "compressor",
        "&Compress dynamics",
        "Evens out loud and quiet passages so nothing jumps out or disappears.",
    ),
    (
        "speech_normalize",
        "S&peech leveling",
        "Brings each phrase to a similar level, "
        "quickly -- good for a speaker who drifts away from the microphone.",
    ),
    (
        "leveler",
        "Night m&ode leveler",
        "Slowly rides the volume so quiet parts come "
        "up and loud parts come down: listening at low volume.",
    ),
    (
        "limiter",
        "Peak li&miter",
        "Stops any peak going above -1 dB, so a loudness "
        "boost can never clip. Recommended whenever loudness or gain is on.",
    ),
)


class ConverterEffectsDialog(wx.Dialog):
    """Every effect, one page. :meth:`result` reads it back."""

    def __init__(self, parent: Any, dsp: DspOptions, *, start_s: float, end_s: float) -> None:
        super().__init__(
            parent,
            title=EFFECTS_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.custom_effects",
        )
        self._base = dsp
        root = wx.BoxSizer(wx.VERTICAL)
        self._boxes: dict[str, wx.CheckBox] = {}
        for field_name, label, help_text in _SWITCHES:
            box = wx.CheckBox(self, label=label)
            box.SetValue(bool(getattr(dsp, field_name)))
            box.SetHelpText(help_text)
            set_accessible_name(box, label)
            root.Add(box, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self._boxes[field_name] = box

        self._loudness_values = [value for value, _label in loudness_choices()]
        root.Add(wx.StaticText(self, label="&Loudness target:"), 0, wx.LEFT | wx.TOP, 8)
        self._loudness = wx.Choice(self, choices=[label for _v, label in loudness_choices()])
        current = dsp.loudness if dsp.loudness in self._loudness_values else ""
        self._loudness.SetSelection(self._loudness_values.index(current))
        set_accessible_name(self._loudness, "Loudness target")
        self._loudness.SetHelpText(
            "Makes every file the same perceived loudness. -16 LUFS suits podcasts "
            "and phones, -20 is Audible's ACX window, -14 is where music services "
            "play, and -23 is the television and radio standard."
        )
        root.Add(self._loudness, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # (attribute, label, low, high, step, value, F1 sentence). The label is
        # created before its control on every row (A11Y-Z-ORDER).
        rows = (
            (
                "_gain",
                "&Gain in decibels:",
                -30.0,
                30.0,
                0.5,
                dsp.gain_db,
                "A flat volume change, -30 to +30 dB. 0 changes nothing.",
            ),
            (
                "_tempo",
                "Pl&ayback speed (1.0 is unchanged):",
                0.5,
                2.0,
                0.05,
                dsp.tempo,
                "Faster or slower without changing pitch, from half to double speed.",
            ),
            (
                "_fade_in",
                "Fade &in, seconds:",
                0.0,
                30.0,
                0.5,
                dsp.fade_in_s,
                "Fades each file in from silence over this many seconds.",
            ),
            (
                "_fade_out",
                "&Fade out, seconds:",
                0.0,
                30.0,
                0.5,
                dsp.fade_out_s,
                "Fades each file out to silence over its last seconds.",
            ),
            (
                "_start",
                "&Keep from, seconds into each file:",
                0.0,
                86400.0,
                1.0,
                start_s,
                "Starts every converted file this many seconds in. 0 keeps the "
                "beginning. Handy for trimming an intro, or making a ringtone.",
            ),
            (
                "_end",
                "Keep &until, seconds (0 for the end):",
                0.0,
                86400.0,
                1.0,
                end_s,
                "Stops every converted file at this many seconds. 0 keeps everything to the end.",
            ),
        )
        for attr, label, low, high, step, value, help_text in rows:
            root.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 8)
            ctrl = wx.SpinCtrlDouble(self, min=low, max=high, inc=step)
            ctrl.SetDigits(1 if step < 1 else 0)
            ctrl.SetValue(value)
            set_accessible_name(ctrl, label)
            ctrl.SetHelpText(help_text)
            root.Add(ctrl, 0, wx.LEFT | wx.RIGHT, 8)
            setattr(self, attr, ctrl)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="OK",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        self.SetSizerAndFit(root)

    def result(self) -> tuple[DspOptions, float, float]:
        """``(effects, keep from, keep until)`` as the dialog now says."""
        values = {name: box.GetValue() for name, box in self._boxes.items()}
        dsp = replace(
            self._base,
            loudness=self._loudness_values[max(0, self._loudness.GetSelection())],
            gain_db=float(self._gain.GetValue()),
            tempo=float(self._tempo.GetValue()),
            fade_in_s=float(self._fade_in.GetValue()),
            fade_out_s=float(self._fade_out.GetValue()),
            **values,
        )
        start = float(self._start.GetValue())
        end = float(self._end.GetValue())
        return dsp, start, end if end > start else 0.0


def edit_effects(
    host: Any, dsp: DspOptions, *, start_s: float, end_s: float
) -> tuple[DspOptions, float, float] | None:
    """Show Custom Effects through the host; ``None`` when cancelled."""
    dialog = ConverterEffectsDialog(host.frame, dsp, start_s=start_s, end_s=end_s)
    try:
        if (
            host._show_modal_dialog(dialog, EFFECTS_TITLE) != wx.ID_OK
        ):  # dialog_button_contract: exempt
            return None
        return dialog.result()
    finally:
        dialog.Destroy()


class ConverterTextDialog(wx.Dialog):
    """A read-only report with Copy and Close."""

    def __init__(self, parent: Any, title: str, text: str, *, copy: Callable[[str], bool]) -> None:
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.report",
        )
        self._text = text
        self._copy = copy
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self, label="&Details:"), 0, wx.LEFT | wx.TOP, 8)
        self._body = wx.TextCtrl(
            self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(560, 320)
        )
        set_accessible_name(self._body, "Details")
        self._body.SetHelpText(
            "Read-only. Arrow through it line by line, or press Copy to put all of "
            "it on the clipboard -- for an email to support, for example."
        )
        root.Add(self._body, 1, wx.EXPAND | wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(self, label="C&opy All")
        copy_btn.SetHelpText("Puts the whole report on the clipboard.")
        close_btn = wx.Button(self, wx.ID_CANCEL, label="Close")
        close_btn.SetHelpText("Closes this window.")
        row.Add(copy_btn, 0, wx.RIGHT, 6)
        row.Add(close_btn, 0)
        root.Add(row, 0, wx.ALL | wx.EXPAND, 8)
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        bind_close_button(self, close_btn, modeless=False)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(root)
        self._body.SetFocus()

    def _on_copy(self, _event: Any) -> None:
        if self._copy(self._text):
            self._body.SetFocus()


def show_text(host: Any, title: str, text: str) -> None:
    """Show *text* in the read-only report window, titled *title*."""
    dialog = ConverterTextDialog(host.frame, title, text, copy=host._copy_to_clipboard)
    try:
        host._show_modal_dialog(dialog, title)  # dialog_button_contract: exempt
    finally:
        dialog.Destroy()
