"""The Chapters group in Podcast Settings: every chapter switch, in one place.

Until now not one ``chapters_*`` setting had a control. All six were live --
the cascade reads them on every episode -- and all six were invisible, which
makes them worse than absent: a listener whose chapters are slow, or missing,
or being worked out when they did not want them to be, had no way to find the
switch that says so. A setting nobody can reach is a bug with a default.

**One question first, then the details.** "How hard should I look?" is the only
choice most people will ever want to make, and everything else is derived from
it (:mod:`quill.core.podcasts.inference_budget`). So Effort leads, its plain
consequence is spoken beneath it, and the individual sources follow for the
minority who want to say "never scan the audio" and mean it.

**The source switches disable, they do not deprioritise.** Turning one off is
obeyed even under Deep. That asymmetry is deliberate and is why they are
checkboxes rather than a second effort dial: "never" is a thing a person can
say about their own machine, and an app that quietly overrode it under a higher
effort would be lying about what the box does.

Its own module because ``podcast_settings_dialog`` is at its GATE-11 ceiling,
and because the group is a self-contained unit: build it, read its values back,
nothing else.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.inference_budget import BUDGET_LABELS, BUDGETS, describe_plan, for_budget

#: "Work chapters out" -- when, in the listener's terms.
_AUTO_VALUES = ("off", "when_downloaded", "always")
_AUTO_LABELS = (
    "Never -- only show chapters a podcast published",
    "For episodes I have downloaded",
    "For every episode",
)


class ChapterSettingsGroup:
    """The Chapters box: build it from settings, read the settings back out."""

    def __init__(self, dialog: Any, settings: Any) -> None:
        import wx

        self._wx = wx
        box = wx.StaticBoxSizer(wx.VERTICAL, dialog, "Chapters")

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(dialog, label="Work chapters &out:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._auto = wx.Choice(dialog, choices=list(_AUTO_LABELS))
        self._auto.SetName(
            "When QUILL Cast should work chapters out for itself. A published "
            "chapter list is always shown whatever this says; this only governs "
            "the episodes that have none."
        )
        current = str(getattr(settings, "chapters_auto", "when_downloaded"))
        self._auto.SetSelection(_AUTO_VALUES.index(current) if current in _AUTO_VALUES else 1)
        grid.Add(self._auto, 1, wx.EXPAND)

        grid.Add(wx.StaticText(dialog, label="How hard to &look:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._effort = wx.Choice(dialog, choices=[BUDGET_LABELS[name] for name in BUDGETS])
        self._effort.SetName(
            "How long you are willing to wait. Quick uses only what is already "
            "here. Thorough fetches a published transcript and works the sections "
            "out of the words. Deep transcribes the episode on this machine, "
            "which takes minutes and can be cancelled."
        )
        effort = str(getattr(settings, "chapters_effort", "thorough"))
        self._effort.SetSelection(BUDGETS.index(effort) if effort in BUDGETS else 1)
        grid.Add(self._effort, 1, wx.EXPAND)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 6)

        # What the chosen effort will actually do, in a sentence that changes
        # with the choice. "Thorough" on its own does not tell somebody whether
        # their laptop is about to spend a minute on this.
        self._plan = wx.StaticText(dialog, label=describe_plan(for_budget(effort)))
        self._plan.SetName("What this effort level will do")
        box.Add(self._plan, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self._effort.Bind(wx.EVT_CHOICE, lambda _event: self._refresh_plan())

        self._show_notes = self._check(
            dialog,
            box,
            "Use timestamps and the running order in the show &notes",
            "Chapter times a publisher typed into the episode description, and "
            "the running order they wrote in prose. These carry titles a person "
            "wrote, so they are worth more than anything worked out.",
            bool(getattr(settings, "chapters_use_show_notes", True)),
        )
        self._transcript = self._check(
            dialog,
            box,
            "Use the episode &transcript",
            "Work the sections out from where the subject changes in the words. "
            "Fetches a published transcript if the episode has one.",
            bool(getattr(settings, "chapters_use_transcript", True)),
        )
        self._scan_audio = self._check(
            dialog,
            box,
            "Listen to the audio for &pauses",
            "A last resort, and off unless you choose Deep. Measured against "
            "hand-built chapter lists it scored worse than dividing the episode "
            "into equal parts, so it is offered only when there is nothing else.",
            bool(getattr(settings, "chapters_scan_audio", True)),
        )
        self._announce = self._check(
            dialog,
            box,
            "&Say how many chapters were found",
            "One short sentence when a scan finishes. The list is there when you "
            "want it either way.",
            bool(getattr(settings, "chapters_announce", True)),
        )

        preview_row = wx.BoxSizer(wx.HORIZONTAL)
        preview_row.Add(
            wx.StaticText(dialog, label="Chapter pre&view length (seconds):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._preview = wx.SpinCtrl(dialog, min=3, max=60)
        self._preview.SetValue(int(getattr(settings, "chapters_preview_seconds", 10) or 10))
        self._preview.SetName(
            "How much Preview plays when you check a chapter mark in Review "
            "Chapters. It plays this many seconds before the mark and the same "
            "again after it, then stops, and your place in the episode does not "
            "move. Both sides, because the question is whether the programme "
            "turns at that point, and that needs the end of what came before."
        )
        preview_row.Add(self._preview, 0)
        box.Add(preview_row, 0, wx.ALL, 6)

        self.sizer = box

    def _check(self, dialog: Any, box: Any, label: str, name: str, value: bool) -> Any:
        wx = self._wx
        control = wx.CheckBox(dialog, label=label)
        control.SetName(name)
        control.SetValue(value)
        box.Add(control, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        return control

    def _refresh_plan(self) -> None:
        index = self._effort.GetSelection()
        name = BUDGETS[index] if 0 <= index < len(BUDGETS) else "thorough"
        self._plan.SetLabel(describe_plan(for_budget(name)))

    def values(self) -> dict[str, object]:
        """The group's settings, ready for ``dataclasses.replace``."""
        auto_index = self._auto.GetSelection()
        effort_index = self._effort.GetSelection()
        return {
            "chapters_auto": _AUTO_VALUES[auto_index] if auto_index >= 0 else "when_downloaded",
            "chapters_effort": BUDGETS[effort_index] if effort_index >= 0 else "thorough",
            "chapters_use_show_notes": self._show_notes.GetValue(),
            "chapters_use_transcript": self._transcript.GetValue(),
            "chapters_scan_audio": self._scan_audio.GetValue(),
            "chapters_announce": self._announce.GetValue(),
            "chapters_preview_seconds": self._preview.GetValue(),
        }
