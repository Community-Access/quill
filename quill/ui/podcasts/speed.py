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


def speed_context(host: Any) -> tuple[Any, Any]:
    """``(show, effective settings)`` the speed commands act on.

    The playing show's own override if something is playing, otherwise the
    shared default -- the same resolution Sound Enhancements uses.
    """
    controller = getattr(host, "_podcast_controller", None)
    show_id = controller.state.show_id if controller is not None else None
    show = host._podcast_library.find_show(show_id) if show_id else None
    settings = (
        host._podcast_library.effective_settings(show)
        if show is not None
        else host._podcast_library.settings
    )
    return show, settings


def apply_speed(host: Any, speed: float) -> None:
    """Set the speed in whichever scope is in force, and say which."""
    show, _settings = speed_context(host)
    resolved = clamp_speed(speed)
    if show is not None:
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
    _show, settings = speed_context(host)
    if settings.speed >= SPEED_MAX:
        host._announce(f"Already at the fastest speed, {SPEED_MAX:g}x")
        return
    apply_speed(host, settings.speed + SPEED_STEP)


def speed_down(host: Any) -> None:
    _show, settings = speed_context(host)
    if settings.speed <= SPEED_MIN:
        host._announce(f"Already at the slowest speed, {SPEED_MIN:g}x")
        return
    apply_speed(host, settings.speed - SPEED_STEP)


def speed_reset(host: Any) -> None:
    apply_speed(host, 1.0)
