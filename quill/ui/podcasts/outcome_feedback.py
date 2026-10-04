"""A one-key action's outcome as a sound, words, or both (qc.md 18.7).

QUILL Cast's own *When an action works* choice (``PodcastHistory.action_feedback``),
resolved through the family's one :func:`quill.core.action_feedback.resolve`, so
the rules are the editors' rules: a sound with no clip in the pack speaks
instead, *silent* stays silent, and a failure is always spoken the first time
(:func:`~quill.core.action_feedback.resolve_failure`). Cast starts on *both*,
so turning the earcons on took nothing away from anybody who listens for the
words.
"""

from __future__ import annotations

from typing import Any

__all__ = ["say_failure", "say_outcome"]


def _speak(host: Any, message: str, sound: str) -> None:
    """The host's announce, with the earcon when it takes one.

    A dialog's announce callback takes only the words; the app frame's takes
    a ``sound=`` too. A sound the callback cannot take is posted on its own.
    """
    announce = host._announce
    if not sound:
        announce(message)
        return
    try:
        announce(message, sound=sound)
    except TypeError:
        from quill.ui.companion_cues import post_cue

        post_cue(sound)
        announce(message)


def _mode(host: Any) -> str:
    history = getattr(host, "_podcast_history", None)
    return str(getattr(history, "action_feedback", "both") or "both")


def _has_sound(event: str) -> bool:
    try:
        from quill.ui.sound_manager import has_sound_for

        return bool(has_sound_for(event))
    except Exception:  # noqa: BLE001 - no sound stack means no sound
        return False


def say_outcome(host: Any, message: str, *, sound: str) -> None:
    """An action worked: *sound*, *message*, or both, by the listener's choice."""
    event = str(sound)
    from quill.core.action_feedback import resolve

    play, speak = resolve(_mode(host), has_sound=_has_sound(event))
    if speak:
        _speak(host, message, event if play else "")
        return
    if play:
        from quill.ui.companion_cues import post_cue

        post_cue(event)
    status = getattr(host, "_set_status", None)
    if callable(status):
        status(message)


def say_failure(host: Any, message: str, *, repeated: bool = False) -> None:
    """An action did not work: always words the first time, with the error sound."""
    from quill.core.action_feedback import resolve_failure
    from quill.core.sound_events import SoundEvent

    event = SoundEvent.ERROR.value
    play, speak = resolve_failure(_mode(host), has_sound=_has_sound(event), repeated=repeated)
    if speak:
        _speak(host, message, event if play else "")
    elif play:
        from quill.ui.companion_cues import post_cue

        post_cue(event)
