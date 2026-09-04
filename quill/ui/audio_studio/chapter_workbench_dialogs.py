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
from quill.core.speech.audio_tags import format_time_precise, parse_time
from quill.core.speech.chapters import Chapter
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


class ChapterDetailsDialog(wx.Dialog):
    """Type a chapter's title, exact start and end, and its Podcasting 2.0 extras.

    Its own class so its mnemonics are scoped to it, and so the Workbench does
    not grow a sixth inline form it would then have to keep aligned.
    """

    def __init__(
        self,
        parent: wx.Window,
        chapter: Chapter,
        *,
        lower_ms: int,
        upper_ms: int,
    ) -> None:
        super().__init__(
            parent,
            title=str(_("Edit chapter")),
            style=wx.DEFAULT_DIALOG_STYLE,
            name="audio_studio.chapter_details",
        )
        from quill.ui.audio_studio.pages_base import set_accessible_name

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self,
                label=_(
                    "Times are hours:minutes:seconds.milliseconds. This chapter "
                    "may run between {lower} and {upper}."
                ).format(
                    lower=format_time_precise(lower_ms),
                    upper=format_time_precise(upper_ms),
                ),
                name="audio_studio.chapter_details_range",
            ),
            0,
            wx.ALL,
            10,
        )
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)

        def row(label: str, value: str, help_text: str) -> wx.TextCtrl:
            # Label first, then the control. The control is built here rather
            # than handed in, which is what keeps check_dialog_zorder.py happy
            # and, more to the point, what makes the screen reader pair them.
            grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(self, value=value)
            ctrl.SetHelpText(help_text)
            set_accessible_name(ctrl, label.replace("&", "").rstrip(": "))
            grid.Add(ctrl, 0, wx.EXPAND)
            return ctrl

        self._title = row(
            _("&Title:"),
            chapter.title,
            "The chapter's name, as every player will announce it.",
        )
        self._start = row(
            _("&Start:"),
            format_time_precise(chapter.start_ms),
            "Where this chapter begins. Moving it moves the end of the chapter "
            "before it, so the book stays gapless.",
        )
        self._end = row(
            _("&End:"),
            format_time_precise(chapter.end_ms),
            "Where this chapter ends. Moving it moves the start of the chapter after it.",
        )
        self._url = row(
            _("&Link:"),
            chapter.url,
            "An optional web link for this chapter, carried in the Podcasting "
            "2.0 chapters file. Players that support it show a button.",
        )
        self._image = row(
            _("&Image:"),
            chapter.image,
            "An optional image address for this chapter, carried in the "
            "Podcasting 2.0 chapters file.",
        )
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self, wx.ID_OK, label=_("OK"))
        ok_btn.SetHelpText("Applies these chapter details to the list.")
        cancel_btn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
        cancel_btn.SetHelpText("Leaves the chapter exactly as it was.")
        buttons.AddStretchSpacer()
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label=str(_("OK")),
            cancel_id=wx.ID_CANCEL,
            cancel_label=str(_("Cancel")),
        )
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()

    def values(self) -> tuple[str, int | None, int | None, str, str]:
        """Title, start ms, end ms, link, image. An unparseable time reads None."""
        return (
            self._title.GetValue().strip(),
            parse_time(self._start.GetValue()),
            parse_time(self._end.GetValue()),
            self._url.GetValue().strip(),
            self._image.GetValue().strip(),
        )
