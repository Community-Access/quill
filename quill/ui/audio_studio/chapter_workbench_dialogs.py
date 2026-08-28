"""Modal helper dialogs for the Chapter Workbench.

Extracted from :mod:`quill.ui.audio_studio.chapter_workbench` so the
Workbench module stays within the GATE-11 size budget. Both dialogs are
self-contained: ``SilenceParamsDialog`` asks for the two ffmpeg
silencedetect knobs, and ``AcxResultDialog`` shows the ACX verdict and
recommendations. Neither depends on the Workbench class.
"""

from __future__ import annotations

import wx

from quill.core.i18n import _
from quill.ui.dialog_contract import apply_modal_ids


class SilenceParamsDialog(wx.Dialog):
    """Modal that asks for the two ffmpeg silencedetect knobs.

    Returns ``(noise_db, min_silence_s)`` on OK. The defaults match
    :func:`quill.core.speech.silence.detect_silence_chapters` so a brand-new
    user gets the same result the core ships; lowering noise_db makes the
    scan more sensitive, raising min_silence_s only counts real pauses.
    """

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(
            parent,
            title=str(_("Propose chapters from silences")),
            style=wx.DEFAULT_DIALOG_STYLE,
            name="audio_studio.workbench_silence_params",
        )
        from quill.ui.audio_studio.pages_base import set_accessible_name

        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=str(
                _(
                    "ffmpeg will scan the recording for silences and propose chapter "
                    "boundaries at the silence midpoints. The proposal lands in the "
                    "Workbench list for review; nothing is applied blind."
                )
            ),
        )
        intro.Wrap(420)
        root.Add(intro, 0, wx.ALL, 12)
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.Add(
            wx.StaticText(self, label=str(_("Noise threshold (dB):"))),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._noise = wx.SpinCtrlDouble(self, min=-60.0, max=-10.0, inc=1.0, initial=-30.0)
        set_accessible_name(self._noise, str(_("Noise threshold (dB)")))
        self._noise.SetHelpText(
            "How quiet the audio must be to count as silence, in decibels; -60 "
            "to -10 in steps of 1, default -30. Lower the number to make the "
            "scan more sensitive (it will find more, quieter pauses); raise it "
            "for noisy recordings so room hiss stops counting as silence."
        )
        grid.Add(self._noise, 0)
        grid.Add(
            wx.StaticText(self, label=str(_("Minimum silence (seconds):"))),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._min_silence = wx.SpinCtrlDouble(self, min=0.1, max=5.0, inc=0.1, initial=0.8)
        set_accessible_name(self._min_silence, str(_("Minimum silence (seconds)")))
        self._min_silence.SetHelpText(
            "How long a pause must last before it can become a chapter "
            "boundary, in seconds; 0.1 to 5 in steps of 0.1, default 0.8. "
            "Raise it so only real between-chapter pauses count, not breaths "
            "between sentences."
        )
        grid.Add(self._min_silence, 0)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self._noise.SetFocus()

    def values(self) -> tuple[float, float]:
        return float(self._noise.GetValue()), float(self._min_silence.GetValue())


class AcxResultDialog(wx.Dialog):
    """Read-only modal that shows the ACX check verdict and any recommendations.

    The verdict is announced when the measurement finishes (the caller fires
    that announce), so the user can dismiss the dialog with Escape and the
    message still reaches them. The dialog exists so the recommendations are
    in front of them, not just spoken once.
    """

    def __init__(self, parent: wx.Window, *, check: object | None) -> None:
        super().__init__(
            parent,
            title=str(_("ACX check")),
            style=wx.DEFAULT_DIALOG_STYLE,
            name="audio_studio.workbench_acx_result",
        )
        from quill.core.speech.loudness import AcxCheck

        root = wx.BoxSizer(wx.VERTICAL)
        if check is None:
            text = wx.StaticText(
                self,
                label=str(
                    _(
                        "The ACX check could not run. Make sure ffmpeg is installed "
                        "and the book file is still on disk."
                    )
                ),
            )
        else:
            assert isinstance(check, AcxCheck)
            verdict = _("passes") if check.ok else _("fails")
            lines: list[str] = [
                _("ACX verdict: {verdict}.").format(verdict=verdict),
                "",
                _(
                    "Integrated loudness: {lufs:.1f} LUFS (target {target} plus or minus {rng})"
                ).format(lufs=check.integrated_lufs, target=-20.0, rng=3.0),
                _("True peak: {peak:.1f} dBFS (max {max})").format(
                    peak=check.true_peak_db, max=-3.0
                ),
                _("Noise floor: {noise:.1f} dBFS (max {max})").format(
                    noise=check.noise_floor_db, max=-60.0
                ),
            ]
            recs = check.recommendations()
            if recs:
                lines.append("")
                lines.append(_("What to fix:"))
                lines.extend(f"- {r}" for r in recs)
            text = wx.StaticText(self, label="\n".join(lines))
        text.Wrap(480)
        root.Add(text, 1, wx.EXPAND | wx.ALL, 12)
        buttons = self.CreateButtonSizer(wx.OK)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
