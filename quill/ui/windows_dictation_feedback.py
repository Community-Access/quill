"""Dictation Settings' feedback choices, and a button to hear them (FUX-08).

Split out of :mod:`quill.ui.windows_dictation_dialog` on 2026-11-24 (GATE-11),
when the button to hear the choices came: what you hear after each phrase,
the start, stop and failure sounds, and saying "Dictation on" and "Dictation
off". Nothing about those three controls changed.

**Hear Start, Phrase and Stop** plays what dictation will do with the choices
as they are in the window now, not as they were saved: dictation starting, a
phrase being written, and dictation stopping, a moment apart, through the
shared :class:`~quill.ui.setting_preview.PreviewSequence`. Pressing it again
or pressing Escape stops it without closing the window, and closing the window
stops it. Nothing is saved until OK, so Cancel keeps what you had. The same
window is Dictation Settings in QUILL, QUILL Lite, QUILL Transcribe and Quill
Inkwell, so all four get it.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.action_feedback import ACTION_FEEDBACK_LABELS
from quill.core.action_feedback import coerce as coerce_feedback
from quill.core.sound_events import SoundEvent
from quill.core.windows_dictation.controller import DEFAULT_PHRASE_FEEDBACK
from quill.ui.setting_preview import PreviewSequence, PreviewStep, edge_step, feedback_step

__all__ = ["PREVIEW_PHRASE", "DictationFeedbackMixin"]

#: What the preview reads back for a phrase when the choice includes speech.
PREVIEW_PHRASE = "This is how a written phrase is read back."


def _has_sound(event: str) -> bool:
    try:
        from quill.ui.sound_manager import has_sound_for

        return bool(has_sound_for(event))
    except Exception:  # noqa: BLE001 - no sound stack: there is no sound
        return False


class DictationFeedbackMixin:
    """The three feedback controls and the Hear button. Needs ``_announce``."""

    _announce: Any

    def _add_feedback_controls(self, root: Any, settings: Any, pad: int) -> None:
        # What you hear after each phrase sits with the other sounds, in the
        # right column: the left one gave its height to Dictation style (D-20).
        feedback_label = wx.StaticText(self, label="After each &phrase is written, give me:")
        self._feedback_values = [str(mode) for mode, _label in ACTION_FEEDBACK_LABELS]
        self.feedback = wx.Choice(self, choices=[label for _mode, label in ACTION_FEEDBACK_LABELS])
        self.feedback.SetHelpText(
            "What you hear each time a phrase goes into the document. A sound is "
            "a short tone. Speech reads back the words that were written, so you "
            "can hear whether they are the words you said. Use headphones if you "
            "choose speech: read back through speakers, the microphone can hear "
            "it and write it down again."
        )
        mode = str(
            coerce_feedback(
                getattr(settings, "windows_dictation_phrase_feedback", DEFAULT_PHRASE_FEEDBACK)
            )
        )
        self.feedback.SetSelection(self._feedback_values.index(mode))
        root.Add(feedback_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, pad)
        root.Add(self.feedback, 0, wx.EXPAND | wx.ALL, pad)

        self.cue_sounds = wx.CheckBox(
            self, label="Play &sounds when dictation starts, stops or fails"
        )
        self.cue_sounds.SetValue(bool(getattr(settings, "windows_dictation_cue_sounds", True)))
        self.cue_sounds.SetHelpText(
            "A rising pair of tones when dictation starts listening, a falling "
            "pair when it stops, and a low double tone when something goes wrong. "
            "A failure is always spoken as well, whatever this is set to."
        )
        root.Add(self.cue_sounds, 0, wx.ALL, pad)

        self.announce = wx.CheckBox(self, label='Say "Dictation on" and "Dictation &off"')
        self.announce.SetValue(bool(getattr(settings, "windows_dictation_announce", True)))
        self.announce.SetHelpText(
            "Speak the words as well as, or instead of, the sounds when dictation "
            "starts and stops. With both off, the check mark on the Dictation "
            "menu item still shows whether it is on."
        )
        root.Add(self.announce, 0, wx.ALL, pad)

        self.hear_feedback = wx.Button(self, label="Hear Start, Phrase and Stop")
        # No access key: the window has none left but Q and Z (GATE-14). Tab
        # reaches it straight after the three choices it plays.
        self.hear_feedback.SetHelpText(
            "Hear what dictation will do with the three choices above as they are "
            "now: dictation starting, a phrase being written, and dictation stopping. "
            "Nothing is saved until OK. Press it again, or Escape, to stop what is left. "
            "With Just write what I say on, a phrase plays nothing, so you hear only "
            "the start and the stop."
        )
        self.hear_feedback.Bind(wx.EVT_BUTTON, self._on_hear_feedback)
        root.Add(self.hear_feedback, 0, wx.ALL, pad)
        self._feedback_preview = PreviewSequence(lambda text: self._announce(text))
        self._feedback_preview.guard(self)

    def feedback_preview_steps(self) -> list[PreviewStep]:
        """What dictation would do with the choices as the window shows them."""
        cue_sounds = bool(self.cue_sounds.GetValue())
        announce = bool(self.announce.GetValue())
        row = self.feedback.GetSelection()
        mode = self._feedback_values[row] if 0 <= row < len(self._feedback_values) else ""
        phrase = feedback_step(
            mode,
            event=SoundEvent.WINDOWS_DICTATION_PHRASE,
            words=PREVIEW_PHRASE,
            has_sound=_has_sound(SoundEvent.WINDOWS_DICTATION_PHRASE),
        )
        continuous = getattr(self, "continuous", None)
        if continuous is not None and continuous.GetValue():
            phrase = PreviewStep()  # a pause does nothing, not even a tone
        return [
            edge_step(
                cue_sounds=cue_sounds,
                announce=announce,
                event=SoundEvent.WINDOWS_DICTATION_ON,
                words="Dictation on.",
                has_sound=_has_sound(SoundEvent.WINDOWS_DICTATION_ON),
            ),
            phrase,
            edge_step(
                cue_sounds=cue_sounds,
                announce=announce,
                event=SoundEvent.WINDOWS_DICTATION_OFF,
                words="Dictation off.",
                has_sound=_has_sound(SoundEvent.WINDOWS_DICTATION_OFF),
            ),
        ]

    def _on_hear_feedback(self, _event: Any) -> None:
        if self._feedback_preview.stop():
            return  # the second press stops it
        self._feedback_preview.play(self.feedback_preview_steps())
