"""Apply a show's volume boost after its player has loaded."""

from __future__ import annotations


def apply(controller: object, settings: object) -> None:
    """Set this podcast's boost on the player. Never raises.

    Off is a real answer that has to be sent -- otherwise a loud show played
    after a quiet one would inherit the quiet one's boost, which is the exact
    complaint a per-show setting exists to prevent.
    """
    from quill.core.podcasts import volume_boost

    setter = getattr(controller, "set_volume_boost", None)
    if not callable(setter):
        return
    level = volume_boost.normalize(getattr(settings, "volume_boost", volume_boost.OFF))
    try:
        setter(volume_boost.multiplier(level))
    except Exception:  # noqa: BLE001 - a boost that will not set is not a failure to play
        return
