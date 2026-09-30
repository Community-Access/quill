"""Playback speed in QUILL Cast, and the scope every speed verb shares.

One scope rule, stated once: the speed commands act on the **playing show's
own override** when something is playing, and on the shared default
otherwise -- the same resolution Sound Enhancements uses, and the same one
:mod:`quill.ui.podcasts.skip_silence` follows, so "faster" and "skip the
pauses" never turn out to have meant different things.

Every step says the speed *and the scope*: "Speed 1.5x for The Daily" and
"Speed 1.5x for every podcast" are different facts, and a listener who cannot
see which show is loaded has no other way to tell them apart. The ends of the
range are announced rather than silently clamped, because a key that stops
doing anything is indistinguishable from a key that stopped working.

Extracted from ``main_frame_podcast_session.py`` under GATE-11.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.models_settings import SPEED_MAX, SPEED_MIN, SPEED_STEP, clamp_speed


def playing_episode(host: Any) -> Any:
    """The episode playing, or ``None``. Needed for per-file speed (R12)."""
    controller = getattr(host, "_podcast_controller", None)
    state = getattr(controller, "state", None)
    show_id = getattr(state, "show_id", None)
    guid = getattr(state, "episode_guid", None)
    if not show_id or not guid:
        return None
    show = host._podcast_library.find_show(show_id)
    return show.find_episode(guid) if show is not None else None


def speed_scope(host: Any) -> tuple[Any, Any, Any]:
    """``(show, episode, effective settings)`` -- what the speed commands act on.

    Three scopes, narrowest first, which is R12: an **imported file** keeps its own
    speed, then the **playing show's** override, then the shared default. A folder
    of lectures and an audiobook sit in the same local show, and they do not want
    the same speed; a subscribed episode has never wanted its own and does not get
    one, because a per-episode speed on a feed is a setting nobody can find again.
    """
    controller = getattr(host, "_podcast_controller", None)
    show_id = getattr(getattr(controller, "state", None), "show_id", None)
    show = host._podcast_library.find_show(show_id) if show_id else None
    episode = playing_episode(host)
    if episode is not None and not bool(getattr(show, "is_local", False)):
        episode = None  # only an imported file may carry its own speed
    settings = (
        host._podcast_library.effective_settings(show)
        if show is not None
        else host._podcast_library.settings
    )
    return show, episode, settings


def speed_context(host: Any) -> tuple[Any, Any]:
    """``(show, effective settings)``. Kept for callers that predate R12."""
    show, _episode, settings = speed_scope(host)
    return show, settings


def current_speed(host: Any) -> float:
    """The speed in force, reading the file's own first."""
    _show, episode, settings = speed_scope(host)
    own = float(getattr(episode, "speed_override", 0.0) or 0.0) if episode is not None else 0.0
    return own or float(getattr(settings, "speed", 1.0) or 1.0)


def apply_speed(host: Any, speed: float) -> None:
    """Set the speed in whichever scope is in force, and say which.

    The scope is always announced, because "1.5x" alone does not say whether the
    listener has just changed one file, one show or everything -- and somebody who
    cannot see which row is loaded has no other way to find out.
    """
    show, episode, _settings = speed_scope(host)
    resolved = clamp_speed(speed)
    if episode is not None:
        episode.speed_override = resolved
        target = "this file only"
    elif show is not None:
        host._podcast_library.apply_show_override(show, speed=resolved)
        target = show.title
    else:
        host._podcast_library.settings.speed = resolved
        target = "every podcast"
    host._save_podcast_library()
    controller = getattr(host, "_podcast_controller", None)
    if controller is not None and controller.state.show_id is not None:
        controller.set_rate(resolved)
    host._announce(f"Speed {resolved:g}x for {target}")


def speed_up(host: Any) -> None:
    current = current_speed(host)
    if current >= SPEED_MAX:
        host._announce(f"Already at the fastest speed, {SPEED_MAX:g}x")
        return
    apply_speed(host, current + SPEED_STEP)


def speed_down(host: Any) -> None:
    current = current_speed(host)
    if current <= SPEED_MIN:
        host._announce(f"Already at the slowest speed, {SPEED_MIN:g}x")
        return
    apply_speed(host, current - SPEED_STEP)


def speed_reset(host: Any) -> None:
    apply_speed(host, 1.0)
