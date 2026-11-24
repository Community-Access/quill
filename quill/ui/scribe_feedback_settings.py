"""Scribe for Documents Options: how progress and results are told (2026-11-23).

The section of :class:`~quill.ui.scribe_options_dialog.ScribeOptionsDialog`
for :mod:`quill.core.scribe.feedback`: for each of a conversion's four
moments, a sound, words, both or neither, in the family's one wording
(:data:`~quill.core.action_feedback.ACTION_FEEDBACK_LABELS`); where stage
feedback is given; and a button to hear the success and the failure sound.
Every Scribe entry point in every app opens the same dialog, so this is the
one place, in QUILL and in QUILL Lite alike.

Built in its own module so the dialog stays readable, and kept to the
dialog's access keys: these labels take S, E, P, H, U, C and L, which nothing
else in that window uses (GATE-14; ``test_options_access_keys_are_unique_in_the_whole_window``
checks the whole built dialog (``test_scribe_feedback_routing.py``), because
the gate scopes a helper class per method and cannot see the two together).

A preview plays through the same sound scheme as the real thing, so its
volume, its App Sounds device and the sound switch are the ones a finished
conversion will use. When it cannot play, it says why in words -- the
outcome of the person's own button press, which the screen reader would not
otherwise tell them (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.action_feedback import ACTION_FEEDBACK_LABELS
from quill.core.scribe.feedback import (
    STAGE_SCOPES,
    FeedbackChoices,
    Moment,
    sound_for,
)
from quill.ui.accessible_group import describe_group

__all__ = ["BOX_LABEL", "FeedbackSection", "preview_sound"]

BOX_LABEL = "Progress and results"

#: Each moment's label in this window, with its access key.
_LABELS: dict[Moment, str] = {
    Moment.STARTED: "When a conversion &starts:",
    Moment.STAGE: "At &each stage, milestone or delay:",
    Moment.FINISHED: "When a conversion finis&hes:",
    Moment.FAILED: "When a conversion fails or needs yo&u:",
}

_HELP: dict[Moment, str] = {
    Moment.STARTED: (
        "What happens when a conversion is sent to Scribe for Documents. The default "
        "is Neither: the Conversions window shows it."
    ),
    Moment.STAGE: (
        "Each stage, the 25, 50 and 75 percent milestones, and a delay: Scribe asking "
        "to slow down, or this computer offline. The default is Neither: read them in "
        "the Conversions window or Scribe Status; a delay is also in the status bar. "
        "A sound is a soft tick, or the progress tone for that milestone."
    ),
    Moment.FINISHED: (
        "When a result is ready. The default is the success sound. With the app's "
        "sounds turned off it is spoken instead; if you switch this sound off in "
        "Sound Scheme there is no sound and no speech. Whatever you choose, the result "
        "is in the status bar and Notifications, and Repeat Last Scribe Message says it "
        "again."
    ),
    Moment.FAILED: (
        "When a conversion fails or waits for you: sign-in expired, out of pages, a "
        "file Scribe refused. The default is the failure sound, different from the "
        "success sound. With the app's sounds turned off it is spoken instead. The "
        "reason is always in the status bar and Notifications."
    ),
}

_MODES = [mode for mode, _label in ACTION_FEEDBACK_LABELS]
_SCOPES = [key for key, _label in STAGE_SCOPES]


def preview_sound(moment: Moment) -> str:
    """Play *moment*'s sound as a conversion would; ``""`` when it played,
    else the sentence that says why it did not."""
    from quill.ui import sound_manager

    event = sound_for(moment)
    which = "success" if moment is Moment.FINISHED else "failure"
    ending = "a finished conversion" if moment is Moment.FINISHED else "a failed conversion"
    if not sound_manager.is_active():
        return f"Sounds are turned off, so nothing played, and {ending} is spoken instead."
    if not sound_manager.has_sound_for(event):
        return (
            f"The sound scheme has no {which} sound, so {ending} is spoken instead. "
            "Sound Scheme can add one."
        )
    if sound_manager.is_event_switched_off(event):
        return (
            f"The {which} sound is switched off in Sound Scheme, so nothing played, "
            f"and {ending} makes no sound."
        )
    from quill.ui.companion_cues import post_cue

    post_cue(event)
    return ""


class FeedbackSection:
    """The controls, in a labelled group; :meth:`choices` reads them back."""

    def __init__(
        self,
        parent: Any,
        choices: FeedbackChoices,
        *,
        say: Callable[[str], None],
    ) -> None:
        self._say = say
        self.sizer = wx.StaticBoxSizer(wx.VERTICAL, parent, BOX_LABEL)
        box = self.sizer.GetStaticBox()
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=6)
        grid.AddGrowableCol(1)
        self.modes: dict[Moment, Any] = {}
        mode_labels = [label for _mode, label in ACTION_FEEDBACK_LABELS]
        for moment in Moment:
            grid.Add(wx.StaticText(box, label=_LABELS[moment]), 0, wx.ALIGN_CENTER_VERTICAL)
            choice = wx.Choice(box, choices=mode_labels)
            choice.SetSelection(_MODES.index(choices.mode(moment)))
            choice.SetHelpText(_HELP[moment])
            grid.Add(choice, 1, wx.EXPAND)
            self.modes[moment] = choice
            if moment is Moment.STAGE:
                grid.Add(
                    wx.StaticText(box, label="Stage feedback a&pplies:"),
                    0,
                    wx.ALIGN_CENTER_VERTICAL,
                )
                self.scope = wx.Choice(box, choices=[label for _key, label in STAGE_SCOPES])
                scope = choices.stage_scope
                self.scope.SetSelection(_SCOPES.index(scope) if scope in _SCOPES else 0)
                self.scope.SetHelpText(
                    "Where stage feedback is given: only while the Conversions window, "
                    "Scribe Status or My Scribe Documents is in front (the default), or "
                    "everywhere, even with another program in front. No effect while "
                    "the stage choice is Neither."
                )
                grid.Add(self.scope, 1, wx.EXPAND)
        self.sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 4)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.play_success = wx.Button(box, label="Play Su&ccess Sound")
        self.play_success.SetHelpText(
            "Plays the sound a finished conversion makes, at the volume and on the "
            "device App Sounds uses, whatever is chosen above. Change it in Sound Scheme."
        )
        self.play_failure = wx.Button(box, label="Play Fai&lure Sound")
        self.play_failure.SetHelpText(
            "Plays the sound a failed conversion, or one that needs you, makes, whatever "
            "is chosen above. Change it in Sound Scheme."
        )
        row.Add(self.play_success, 0, wx.ALL, 4)
        row.Add(self.play_failure, 0, wx.ALL, 4)
        self.sizer.Add(row)
        # Each control says "Progress and results" after its own name, as the
        # rest of Scribe Options does (quill.ui.accessible_group, GATE-GROUP).
        describe_group(
            self.sizer, *self.modes.values(), self.scope, self.play_success, self.play_failure
        )
        self.play_success.Bind(wx.EVT_BUTTON, lambda _e: self.play(Moment.FINISHED))
        self.play_failure.Bind(wx.EVT_BUTTON, lambda _e: self.play(Moment.FAILED))

    def play(self, moment: Moment) -> None:
        said = preview_sound(moment)
        if said:
            self._say(said)

    def choices(self, into: FeedbackChoices | None = None) -> FeedbackChoices:
        made = into if into is not None else FeedbackChoices()
        for moment, choice in self.modes.items():
            made.set_mode(moment, _MODES[max(0, choice.GetSelection())])
        made.stage_scope = _SCOPES[max(0, self.scope.GetSelection())]
        return made
