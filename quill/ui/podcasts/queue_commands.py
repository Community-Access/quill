"""Stepping the Play Queue from the keyboard (ear.md R2, R3).

Three commands, and what each of them says is as much of the design as what it
does. The rule they all follow: **the app says only what the screen reader
cannot.**

* Starting an episode already announces its title and show through
  ``start_episode_playback``, so Next in Queue adds nothing of its own. Saying
  "Next" as well would be a word the listener has to hear before the fact they
  asked for.
* Restarting says three words, because it is a command whose entire effect is
  invisible: the position moved and nothing on screen changed.
* Either end of the run speaks, with an earcon leading it, because nothing
  changed anywhere and there is no reader utterance to duplicate. Silence there
  is the under-announcing that :mod:`quill.core.action_feedback` describes -- a
  key that stops doing anything is indistinguishable from a key that stopped
  working, which is the argument :mod:`quill.ui.podcasts.speed` already makes
  about the ends of the speed range.
* Mark as Played and Next does **not** say "Marked as played". It is a key
  pressed in runs, and two facts in one breath is one too many; the mark is
  verifiable in the row just left, and the next episode's title proves the
  command fired.

The host-function shape, not a mixin, matching :mod:`quill.ui.podcasts.speed`:
the module stays out of the mixin's line count and every command is callable
with a fake host in a test.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.queue_steps import step_after_finishing, step_next, step_previous
from quill.core.sound_events import SoundEvent

__all__ = [
    "QueueRunCommandsMixin",
    "sleep_timer_episode_changed",
    "sleep_timer_keep_awake",
    "mark_played_and_next",
    "next_in_queue",
    "previous_in_queue",
]


def _playing(host: Any) -> tuple[Any, str, str]:
    """``(controller, show_id, episode_guid)`` for whatever is playing."""
    controller = getattr(host, "_podcast_controller", None)
    state = getattr(controller, "state", None)
    return (
        controller,
        getattr(state, "show_id", None) or "",
        getattr(state, "episode_guid", None) or "",
    )


def _say_edge(host: Any, message: str) -> None:
    """An edge of the run: the words, with the matching house earcon in front.

    ``DOCUMENT_TOP`` / ``DOCUMENT_BOTTOM`` rather than a new Cast-only event: an
    edge is not a new *kind* of event, and a new enum member would be a new row
    in everybody's Sound Scheme window.
    """
    event = SoundEvent.DOCUMENT_TOP if message.startswith("Start") else SoundEvent.DOCUMENT_BOTTOM
    try:
        host._announce(message, sound=event)
    except TypeError:
        # A host whose _announce takes words only. The words are the part that
        # carries the meaning, so losing the earcon is never worth a crash.
        host._announce(message)


def _play(host: Any, step: Any) -> None:
    from quill.ui.podcasts.show_actions import start_episode_playback

    host._save_podcast_library()
    start_episode_playback(host._podcast_controller, host._podcast_library, step.show, step.episode)


def next_in_queue(host: Any) -> None:
    """Play the next slot in the queue, leaving the run intact."""
    _controller, show_id, guid = _playing(host)
    step = step_next(host._podcast_library, show_id, guid)
    if step.is_edge:
        _say_edge(host, step.message)
        return
    _play(host, step)


def previous_in_queue(host: Any) -> None:
    """Restart this episode, or play the slot before it.

    The five-second rule, which every player has and nobody has to be told: a
    listener two seconds in meant "the one before", and a listener ten minutes in
    meant "start this again".
    """
    controller, show_id, guid = _playing(host)
    position = int(controller.position_ms()) if controller is not None else 0
    step = step_previous(host._podcast_library, show_id, guid, position)
    if step.kind == "restart":
        controller.seek(0)
        title = getattr(getattr(host, "_podcast_current_episode", None), "title", "")
        host._announce(f"Restarted {title}" if title else "Restarted from the beginning")
        return
    if step.is_edge:
        _say_edge(host, step.message)
        return
    _play(host, step)


def mark_played_and_next(host: Any) -> None:
    """Finish this episode and start the next: one key for a listening run.

    Marked played, out of the queue, and the next slot playing -- in that order,
    so "finish this and start the next" is one decision rather than two that can
    disagree about what "next" meant. At the end of the run playback stops and
    says so; there is no wrap.
    """
    controller, show_id, guid = _playing(host)
    if not show_id or not guid:
        host._announce("Nothing is playing.")
        return
    library = host._podcast_library
    show = library.find_show(show_id)
    episode = show.find_episode(guid) if show is not None else None
    if episode is not None:
        episode.played = True
        episode.position_ms = 0
    step, _freed = step_after_finishing(library, show_id, guid)
    if step.kind == "play":
        _play(host, step)
        return
    host._save_podcast_library()
    if controller is not None:
        controller.stop()
    _say_edge(host, "End of queue")


class QueueRunCommandsMixin:
    """The three commands as host methods, for the menu and the palette to bind.

    Thin on purpose, exactly like :class:`quill.ui.main_frame_hosted_ai.HostedAiCommandsMixin`:
    every decision is in the functions above, which a test can call with a fake
    host. A mixin here rather than three more methods in
    ``main_frame_podcast_session.py``, which has sixteen lines of GATE-11
    headroom left, and rather than in ``apps/podcasts.py``, which has three.
    """

    def podcast_next_in_queue(self) -> None:
        next_in_queue(self)

    def podcast_previous_in_queue(self) -> None:
        previous_in_queue(self)

    def podcast_mark_played_and_next(self) -> None:
        mark_played_and_next(self)

    def podcast_sleep_timer_keep_awake(self) -> None:
        sleep_timer_keep_awake(self)

    def podcast_sleep_timer_episode_changed(self) -> None:
        sleep_timer_episode_changed(self)


def sleep_timer_keep_awake(host: Any) -> None:
    """A playback key was used: restart the sleep countdown if asked to (R22).

    Called from the transport commands rather than from the player, because the
    question is "did the listener do something", not "did audio happen": a
    chapter boundary passing is not evidence anybody is awake.

    Silent. Restarting the countdown is what the listener asked for by turning the
    setting on, and announcing it on every skip-forward would be a sentence over
    the top of the episode every fifteen seconds.
    """
    controller = getattr(host, "_sleep_timer_controller", None)
    if controller is None or not getattr(controller, "is_active", False):
        return
    settings = getattr(getattr(host, "_podcast_library", None), "settings", None)
    if not bool(getattr(settings, "sleep_timer_reset_on_use", False)):
        return
    controller.restart()


def sleep_timer_episode_changed(host: Any) -> None:
    """A different episode was chosen: clear the sleep timer if asked to (R22).

    Unlike the reset above this one *does* speak, and the difference is the point:
    cancelling is the end of something the listener set up, and a timer that
    disappeared without a word is a timer they will assume is still running.
    """
    controller = getattr(host, "_sleep_timer_controller", None)
    if controller is None or not getattr(controller, "is_active", False):
        return
    settings = getattr(getattr(host, "_podcast_library", None), "settings", None)
    if not bool(getattr(settings, "sleep_timer_cancel_on_switch", False)):
        return
    controller.cancel()
    host._announce("Sleep timer cancelled, because you chose another episode.")
