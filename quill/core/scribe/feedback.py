"""How Scribe for Documents tells the person about a conversion (2026-11-23).

Jeff, testing QUILL Lite: "do not announce things in the main quill window;
if people want to monitor the status a queue option in a dialog should show
ongoing status", and "give rich settings to allow the user to control
interaction type, sound, speech, both, none, etc. use different sounds for
success and failure."

So a conversion has five **moments**, and each has its own choice in Scribe
for Documents Options, from the family's one feedback vocabulary
(:mod:`quill.core.action_feedback`: a sound, words, both, or neither -- the
same enum and the same chooser wording, never a second set):

=====================  ============================  =========
Moment                 What it covers                Default
=====================  ============================  =========
``started``            a conversion was sent          neither
``stage``              each stage, the 25, 50 and     neither
                       75 percent marks, busy and
                       offline
``finished``           a result is ready (and the     sound
                       batch summary, and what
                       finished while the app was
                       closed)
``failed``             it failed, or it needs the     sound
                       person (sign-in expired, out
                       of pages, a refused file)
``set_finished``       every document of a named set  sound
                       has finished: one cue for the
                       whole set, the failure sound
                       if any of it failed
=====================  ============================  =========

**A set gets one cue** (2026-11-24). The documents of a named set
(:mod:`quill.core.scribe.sets`) are not told one by one as they finish or
fail -- 34 sounds would be noise -- and the set's own moment, when the last
of them is done, is the one cue: the success sound when every document was
made, the failure sound when any was not (:func:`plan`'s *failed*).

**Nothing is spoken by default.** Progress is in the Conversions window and
the Scribe Status dialog, where the person goes to read it; the end of a job
is a short sound, success and failure audibly different
(:data:`MOMENT_SOUNDS`). **The words are never lost**: every finished and
failed sentence also goes to the status bar and to Notifications, and Repeat
Last Scribe Message says it again, whatever was chosen here (FUX-04).

Stage feedback has one more choice, :data:`STAGE_SCOPES`: only while a Scribe
for Documents window (Conversions, Status, Documents in My Scribe Account) is in front --
the default -- or everywhere, even with another program in front.

**A deliberate exception to one family rule.** :mod:`~quill.core.
action_feedback` speaks every failure in every mode but ``silent``
(:func:`~quill.core.action_feedback.resolve_failure`), because "it did not
work" is not a cue. That rule is about a key the person just pressed, whose
failure they are waiting to hear. A conversion fails minutes later, in the
background, often while the person is doing something else -- which is what
Jeff asked not to be interrupted by -- and the failure sound is its own,
distinct from the success sound, with the sentence one key away. So the
``failed`` moment follows :func:`~quill.core.action_feedback.resolve` like the
others. The other half of that module's rules holds: a ``sound`` choice with
no clip in the loaded pack speaks instead, and ``silent`` is silent.

wx-free, strict-typed, no I/O.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from quill.core.action_feedback import ActionFeedback, coerce, resolve
from quill.core.sound_events import SoundEvent, progress_sound_event

__all__ = [
    "DEFAULT_STAGE_SCOPE",
    "EVERYWHERE",
    "MOMENT_LABELS",
    "MOMENT_SOUNDS",
    "NOTHING",
    "SCRIBE_WINDOW_ATTR",
    "SCRIBE_WINDOWS",
    "STAGE_SCOPES",
    "Delivery",
    "FeedbackChoices",
    "Moment",
    "from_speak_stages",
    "plan",
    "sound_for",
    "to_speak_stages",
]


class Moment(StrEnum):
    """The five things a conversion can tell the person."""

    STARTED = "started"
    STAGE = "stage"
    FINISHED = "finished"
    FAILED = "failed"
    SET_FINISHED = "set_finished"


#: The chooser's label for each moment, in the order the Options page shows
#: them. No access keys here: the dialog owns its letters (GATE-14).
MOMENT_LABELS: tuple[tuple[Moment, str], ...] = (
    (Moment.STARTED, "When a conversion starts"),
    (Moment.STAGE, "At each stage, milestone or delay"),
    (Moment.FINISHED, "When a conversion finishes"),
    (Moment.FAILED, "When a conversion fails or needs you"),
    (Moment.SET_FINISHED, "When a set of documents finishes"),
)

#: The sound each end of a job plays. Two clearly different cues for success
#: and failure, and a quiet one for a start; stage feedback uses the family's
#: progress ladder (:func:`sound_for`). All are in the sound scheme, so each
#: can be replaced or switched off there.
MOMENT_SOUNDS: Mapping[Moment, str] = {
    Moment.STARTED: SoundEvent.SCRIBE_STARTED.value,
    Moment.FINISHED: SoundEvent.SCRIBE_FINISHED.value,
    Moment.FAILED: SoundEvent.SCRIBE_FAILED.value,
    Moment.SET_FINISHED: SoundEvent.SCRIBE_FINISHED.value,
}

#: Stage feedback only while a Scribe for Documents window is in front.
SCRIBE_WINDOWS = "scribe_windows"
#: Stage feedback wherever the person is.
EVERYWHERE = "everywhere"
STAGE_SCOPES: tuple[tuple[str, str], ...] = (
    (SCRIBE_WINDOWS, "Only while a Scribe for Documents window is in front"),
    (EVERYWHERE, "Everywhere, even when another program is in front"),
)
DEFAULT_STAGE_SCOPE = SCRIBE_WINDOWS

#: A top-level window with this attribute true is a Scribe for Documents
#: window for :data:`SCRIBE_WINDOWS` (Conversions, Status, Documents in My Scribe Account).
SCRIBE_WINDOW_ATTR = "is_scribe_window"

_DEFAULTS: Mapping[Moment, ActionFeedback] = {
    Moment.STARTED: ActionFeedback.SILENT,
    Moment.STAGE: ActionFeedback.SILENT,
    Moment.FINISHED: ActionFeedback.SOUND,
    Moment.FAILED: ActionFeedback.SOUND,
    Moment.SET_FINISHED: ActionFeedback.SOUND,
}


def _mode(value: object, default: ActionFeedback) -> ActionFeedback:
    """*value* as a mode; an unknown value is this moment's default, not the
    family default (which is ``sound`` and would make a start chirp)."""
    if str(value).strip().lower() in {mode.value for mode in ActionFeedback}:
        return coerce(value)
    return default


@dataclass(slots=True)
class FeedbackChoices:
    """The person's choices, as kept in ``scribe/options.json``."""

    started: str = ActionFeedback.SILENT.value
    stage: str = ActionFeedback.SILENT.value
    finished: str = ActionFeedback.SOUND.value
    failed: str = ActionFeedback.SOUND.value
    set_finished: str = ActionFeedback.SOUND.value
    stage_scope: str = DEFAULT_STAGE_SCOPE

    def mode(self, moment: Moment) -> ActionFeedback:
        return _mode(getattr(self, moment.value), _DEFAULTS[moment])

    def set_mode(self, moment: Moment, mode: object) -> None:
        setattr(self, moment.value, _mode(mode, _DEFAULTS[moment]).value)

    def to_dict(self) -> dict[str, str]:
        return {
            **{moment.value: self.mode(moment).value for moment in Moment},
            "stage_scope": self.stage_scope
            if self.stage_scope in dict(STAGE_SCOPES)
            else DEFAULT_STAGE_SCOPE,
        }

    @classmethod
    def from_mapping(cls, data: object) -> FeedbackChoices:
        """Validated: an unknown mode or scope is that field's default."""
        made = cls()
        if not isinstance(data, Mapping):
            return made
        for moment in Moment:
            made.set_mode(moment, data.get(moment.value, _DEFAULTS[moment].value))
        scope = data.get("stage_scope")
        made.stage_scope = scope if scope in dict(STAGE_SCOPES) else DEFAULT_STAGE_SCOPE
        return made


def from_speak_stages(old: object) -> FeedbackChoices:
    """The new choices for a file written before them (``speak_stages`` only).

    ``front`` was the default and every file holds it, so it cannot be told
    apart from a choice: it becomes the new defaults. ``never`` was a choice
    and the new default agrees with it. ``always`` was a choice for *more*
    speech -- every stage, even with another program in front -- from someone
    who also had the start, the result and every error spoken: they keep all
    of it, and get the new success and failure sounds with the words.
    """
    if old == "always":
        return FeedbackChoices(
            started=ActionFeedback.SPEECH.value,
            stage=ActionFeedback.SPEECH.value,
            finished=ActionFeedback.BOTH.value,
            failed=ActionFeedback.BOTH.value,
            stage_scope=EVERYWHERE,
        )
    return FeedbackChoices()


def to_speak_stages(choices: FeedbackChoices) -> str:
    """The old field's nearest value, still written for an older build."""
    if choices.mode(Moment.STAGE) is ActionFeedback.SILENT:
        return "never"
    return "always" if choices.stage_scope == EVERYWHERE else "front"


def sound_for(moment: Moment, percent: int = 0, *, failed: bool = False) -> str:
    """The sound event for *moment*; a stage is the progress ladder's step at
    *percent*, or the working tick for a stage with no percent; a set that
    finished with any document *failed* has the failure sound."""
    if moment is Moment.STAGE:
        return progress_sound_event(percent) or SoundEvent.PROGRESS_TICK.value
    if moment is Moment.SET_FINISHED and failed:
        return MOMENT_SOUNDS[Moment.FAILED]
    return MOMENT_SOUNDS[moment]


@dataclass(frozen=True, slots=True)
class Delivery:
    """What to do for one moment: the sound to play ("" for none), and whether
    to speak the sentence (through the announcement service, so braille too)."""

    sound: str
    speak: bool


NOTHING = Delivery("", False)


def plan(
    choices: FeedbackChoices,
    moment: Moment,
    *,
    has_sound: Callable[[str], bool],
    scribe_window_in_front: bool,
    percent: int = 0,
    failed: bool = False,
) -> Delivery:
    """The delivery for *moment* under *choices* (*failed*: a set that ended
    with a document not made, which has the failure sound).

    *has_sound* answers whether the loaded pack can play an event; a ``sound``
    choice for an event it cannot play speaks instead (the family rule).
    """
    if moment is Moment.STAGE and choices.stage_scope != EVERYWHERE and not scribe_window_in_front:
        return NOTHING
    event = sound_for(moment, percent, failed=failed)
    play, speak = resolve(choices.mode(moment), has_sound=bool(event) and has_sound(event))
    return Delivery(event if play else "", speak)
