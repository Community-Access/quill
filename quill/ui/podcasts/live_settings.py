"""A saved podcast setting reaches the episode that is already playing.

Reported by Chris (2026-11-19): in Quill Cast, Settings for This Podcast set to
1.5x saved, said it was saved, and the episode went on at its old speed; only
Speed Up or Speed Down, which talk to the player directly, made it change.
Every settings window had the same gap. The player is told a podcast's speed,
equaliser, compressor, Skip Silence and Volume Boost once, when an episode
starts (:func:`quill.ui.podcasts.show_actions.start_episode_playback`), and
nothing told it again when one of them was saved somewhere else: Settings for
This Podcast, Preferences' shared defaults, a folder's settings, Change
Speed..., Settings by Name.

So the save itself carries the change. :func:`remember_applied` notes what the
episode was started with; every save goes through ``_save_podcast_library``,
which calls :func:`reapply_saved_settings`; and that pushes **only the fields
whose resolved value changed** since then. Diffing, rather than pushing
everything on every save, is what keeps this safe: a feed refresh or a marked
episode saves the library too, and must not undo a per-file speed, reset a
scan in progress, or restart the audio relay for nothing.

No ``wx``: it talks to the controller the host already has.
"""

from __future__ import annotations

from typing import Any

__all__ = ["AUDIO_FIELDS", "reapply_saved_settings", "remember_applied"]

#: The fields that change what is heard through the relay; any one of them
#: means a reload at the current position (the relay cannot be altered live).
AUDIO_FIELDS = (
    "eq_bass_db",
    "eq_mid_db",
    "eq_treble_db",
    "compressor_enabled",
    "smart_speed_enabled",
)

_ATTRIBUTE = "_quill_applied_settings"


def _playing(controller: Any) -> tuple[str, str]:
    state = getattr(controller, "state", None)
    return (str(getattr(state, "show_id", "") or ""), str(getattr(state, "episode_guid", "") or ""))


def remember_applied(controller: Any, settings: Any) -> None:
    """Note the settings the episode now loaded was started with. Never raises.

    Kept with the episode it belongs to, so a later stream or Spotify item
    that this module never started is never handed another podcast's values.
    """
    import copy

    try:
        # A copy: a podcast that follows the shared default is handed the
        # shared record itself, which a Preferences save then changes in place,
        # and a remembered reference would change with it and never differ.
        setattr(controller, _ATTRIBUTE, (_playing(controller), copy.copy(settings)))
    except Exception:  # noqa: BLE001 - a controller that refuses attributes is a test double
        return


def reapply_saved_settings(host: Any) -> list[str]:
    """Push what changed to the playing episode; returns the field names pushed.

    Nothing playing, no episode remembered, or nothing changed: nothing is done.
    Never raises: it runs inside every save, and a save must not fail for it.
    """
    try:
        return _reapply(host)
    except Exception:  # noqa: BLE001 - the library is saved whether or not this worked
        return []


def _reapply(host: Any) -> list[str]:
    controller = getattr(host, "_podcast_controller", None)
    library = getattr(host, "_podcast_library", None)
    if controller is None or library is None:
        return []
    remembered = getattr(controller, _ATTRIBUTE, None)
    playing = _playing(controller)
    if not isinstance(remembered, tuple) or remembered[0] != playing or not playing[0]:
        return []
    applied = remembered[1]
    show_id = playing[0]
    show = library.find_show(show_id)
    settings = library.effective_settings(show) if show is not None else library.settings
    pushed: list[str] = []
    if _changed(applied, settings, "speed") and _push_speed(host, controller):
        pushed.append("speed")
    if _changed(applied, settings, "volume_boost") and _push_boost(controller, settings):
        pushed.append("volume_boost")
    if any(_changed(applied, settings, field) for field in AUDIO_FIELDS):
        if _push_audio(controller, settings):
            pushed.extend(f for f in AUDIO_FIELDS if _changed(applied, settings, f))
    if "speed" not in pushed and _changed(applied, settings, "speed"):
        # Held back (a scan, or a file of its own): keep the old speed in the
        # record so the next save still sees the difference and tries again.
        settings = _with(settings, speed=getattr(applied, "speed", 1.0))
    remember_applied(controller, settings)
    return pushed


def _changed(before: Any, after: Any, field: str) -> bool:
    return getattr(before, field, None) != getattr(after, field, None)


def _with(settings: Any, **values: Any) -> Any:
    import dataclasses

    try:
        return dataclasses.replace(settings, **values)
    except Exception:  # noqa: BLE001 - not a dataclass: keep it as it is
        return settings


def _push_speed(host: Any, controller: Any) -> bool:
    """Set the speed in force on the player, unless a scan or a file's own speed holds it."""
    scan = getattr(host, "_scan_hold", None)
    if scan is not None and getattr(scan, "is_scanning", False):
        return False  # the scan restores its own starting speed when it lets go
    from quill.ui.podcasts.speed import current_speed, speed_scope

    _show, episode, _settings = speed_scope(host)
    if episode is not None and float(getattr(episode, "speed_override", 0.0) or 0.0):
        return False  # an imported file keeps the speed it was given (R12)
    try:
        controller.set_rate(current_speed(host))
    except Exception:  # noqa: BLE001 - a speed that will not set is not a failure to save
        return False
    return True


def _push_boost(controller: Any, settings: Any) -> bool:
    from quill.ui.podcasts.show_actions import _apply_volume_boost

    _apply_volume_boost(controller, settings)
    return True


def _push_audio(controller: Any, settings: Any) -> bool:
    setter = getattr(controller, "set_enhancement", None)
    if not callable(setter):
        return False
    try:
        setter(
            bass_db=settings.eq_bass_db,
            mid_db=settings.eq_mid_db,
            treble_db=settings.eq_treble_db,
            compressor_enabled=settings.compressor(),
            smart_speed_enabled=settings.smart_speed_enabled,
        )
    except Exception:  # noqa: BLE001 - the episode keeps playing as it was
        return False
    return True
