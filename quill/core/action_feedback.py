"""How a key that *did something* reports back: a tone, words, both, or nothing.

Some commands change the document and change nothing a screen reader announces.
Focus does not move, no control gains a name, no selection changes -- so a copy,
a paste, an undo and a started selection are, to a listener, indistinguishable
from a key that did not work at all. QUILL's answer has been an earcon, and it is
a good answer: a tone is instant, it does not interrupt speech mid-sentence, and
it costs nothing to hear a hundred times an hour.

It is not everyone's answer. A tone has to be *learned* before it means anything,
and someone meeting the app this week would rather be told "Copied" than taught
eleven chimes. Someone else has the earcons by heart and finds being told
"Copied" on every Ctrl+C intolerable within a minute -- which is exactly why the
words were left out in the first place. Both of those people are right, and the
disagreement is not settleable in the code, so it becomes a setting.

Four modes, and the fourth is the point of having an enum rather than a bool:

``sound``
    The tone alone. The default, because it is what QUILL has always done and a
    setting must not change behaviour for anybody who has not touched it.
``speech``
    The words alone -- for someone who has not learned the pack, or who has
    turned the audio device off and still wants to know the key landed.
``both``
    Both, tone first.
``silent``
    Neither. Not a joke option: someone recording audio, or sitting in a room
    with other people, wants an editor that does not chirp -- and reaching for
    the system volume also silences the screen reader, which is not the same
    request.

**A mode only governs a moment that has both to offer.** ``sound`` on a command
with no earcon in the pack must not silence its words, or turning the setting to
its own default would make the app quieter than the day before. So the choice is
resolved against what the call site actually has -- :func:`resolve` -- and never
read as a global on/off. Failure and information stay outside this entirely: a
command that could not do what was asked says so in words in every mode, because
"it did not work" is not a cue and no tone has ever carried it.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ACTION_FEEDBACK_LABELS",
    "ActionFeedback",
    "coerce",
    "resolve",
]


class ActionFeedback(StrEnum):
    """What a command with both a tone and a phrase available should do."""

    SOUND = "sound"
    SPEECH = "speech"
    BOTH = "both"
    SILENT = "silent"


#: The wording a chooser shows, in the order it should show them. Written here
#: rather than in the dialog so both editors' preference panes read from one
#: list -- two panes that drifted apart would offer the same setting under
#: different names, which reads as two settings.
ACTION_FEEDBACK_LABELS: tuple[tuple[ActionFeedback, str], ...] = (
    (ActionFeedback.SOUND, "Play a sound"),
    (ActionFeedback.SPEECH, "Speak the action"),
    (ActionFeedback.BOTH, "Both a sound and speech"),
    (ActionFeedback.SILENT, "Neither"),
)


def coerce(value: object) -> ActionFeedback:
    """The mode *value* names, or the default when it names nothing.

    Settings arrive from a JSON file a person may have edited, so an unknown
    string is an ordinary event rather than an error: it becomes the default,
    which is the behaviour the app had before the setting existed.
    """
    try:
        return ActionFeedback(str(value).strip().lower())
    except ValueError:
        return ActionFeedback.SOUND


def resolve(mode: object, *, has_sound: bool) -> tuple[bool, bool]:
    """``(play_sound, speak)`` for one moment, given what it has available.

    *has_sound* is whether this particular moment has an earcon to play at all.
    When it does not, ``sound`` falls through to the words rather than to
    silence -- the setting is a choice between two kinds of feedback, never a
    way to end up with none where there was some.
    """
    resolved = coerce(mode)
    if resolved is ActionFeedback.SILENT:
        return (False, False)
    if resolved is ActionFeedback.BOTH:
        return (has_sound, True)
    if resolved is ActionFeedback.SPEECH:
        return (False, True)
    return (True, False) if has_sound else (False, True)
