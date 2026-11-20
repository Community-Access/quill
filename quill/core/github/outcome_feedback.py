"""What the GitHub Workbench plays and says for a result (GH-R-113, GH-R-083).

The Workbench reports everything it does in one sentence, and until now it
only ever spoke them. GH-R-113 asks for its sounds to go through the family's
shared action-feedback setting (:mod:`quill.core.action_feedback`), with a
failure or a count always spoken. This module decides, for one sentence,
which tone it gets and whether it is said:

* **A failure** ("Could not ...") gets the error tone where the setting
  allows sounds, and is always said: no tone has ever carried "it did not
  work", or why.
* **An action that landed** ("Saved ...", "Created ...", "Watching ...")
  gets the task-complete tone. A sentence that names or counts what changed
  is always said too, because no tone carries a name or a number. Only a bare
  acknowledgement (:data:`BARE`: "Saved.", "Copied.") follows the setting
  exactly as the editors' Ctrl+C does: tone, words, both or neither, and a
  tone the pack lacks falls back to words.
* **Anything else** (a prompt, "There is nothing to ...", a description) is
  information. It is said, with no tone, whatever the setting.

The sentence is classified by how it starts, because every one of the
Workbench's sentences is written to start with its verb. A sentence this
cannot place is information, which is the safe side: said, and never
replaced by a tone.

No ``wx``; strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from quill.core.action_feedback import ActionFeedback, coerce, resolve
from quill.core.sound_events import SoundEvent

__all__ = ["BARE", "Outcome", "Plan", "classify", "plan"]


class Outcome(StrEnum):
    FAILURE = "failure"
    DONE = "done"
    INFORMATION = "information"


_FAILURE_STARTS = (
    "could not ",
    "couldn't ",
    "cannot ",
    "can't ",
    "github refused",
    "github said no",
    "github did not ",
    "failed ",
    "the workbench could not ",
    "that did not work",
)

_DONE_STARTS = (
    "added ",
    "approved ",
    "archived ",
    "assigned ",
    "cancelled the ",
    "changed ",
    "closed ",
    "comment posted",
    "copied",
    "converted ",
    "created ",
    "deleted ",
    "dismissed ",
    "exported ",
    "followed ",
    "invited ",
    "locked ",
    "made ",
    "marked ",
    "merged ",
    "moved ",
    "opened ",
    "pinned ",
    "published ",
    "re-ran ",
    "removed ",
    "renamed ",
    "reordered",
    "reopened ",
    "requested ",
    "saved",
    "scheduled ",
    "sent ",
    "sorted ",
    "snoozed",
    "starred ",
    "started ",
    "subscribed ",
    "transferred ",
    "unarchived ",
    "unfollowed ",
    "unlocked ",
    "unpinned ",
    "unstarred ",
    "unsubscribed ",
    "updated ",
    "uploaded ",
    "watch changed",
    "watch removed",
    "watching ",
    "watching:",
)


#: The only results a tone may stand in for: acknowledgements that name nothing.
#: Every other sentence that reports a change names what changed, or counts it,
#: and that is information no tone carries, so it is always said (with the tone
#: as well, where the setting asks for sounds). Kept short on purpose: before
#: GH-R-113 the Workbench said every result, and a setting nobody touched must
#: not make it quieter about anything a person needs to hear.
BARE = frozenset({
    "saved.",
    "copied.",
    "deleted.",
    "done.",
    "removed.",
    "closed.",
    "reopened.",
    "watch removed.",
})


def classify(text: str) -> Outcome:
    """Whether *text* reports a failure, an action that landed, or information."""
    said = text.strip().casefold()
    if said.startswith(_FAILURE_STARTS):
        return Outcome.FAILURE
    if said.startswith(_DONE_STARTS):
        return Outcome.DONE
    return Outcome.INFORMATION


@dataclass(frozen=True, slots=True)
class Plan:
    """The tone to play ("" for none) and whether to say the sentence."""

    sound: str
    speak: bool


def plan(text: str, mode: object, *, has_sound: frozenset[str] | set[str]) -> Plan:
    """What to do for *text* under the action-feedback *mode*.

    *has_sound* is the set of events the loaded pack can play, so a mode that
    asked for a tone the pack lacks says the words instead.
    """
    kind = classify(text)
    if kind is Outcome.INFORMATION or not text.strip():
        return Plan("", True)
    sounds_on = coerce(mode) in (ActionFeedback.SOUND, ActionFeedback.BOTH)
    if kind is Outcome.FAILURE:
        tone = SoundEvent.ERROR if sounds_on and SoundEvent.ERROR in has_sound else ""
        return Plan(str(tone), True)
    event = SoundEvent.TASK_COMPLETE
    if text.strip().casefold() not in BARE:
        return Plan(str(event) if sounds_on and event in has_sound else "", True)
    play, speak = resolve(mode, has_sound=event in has_sound)
    return Plan(str(event) if play else "", speak)
