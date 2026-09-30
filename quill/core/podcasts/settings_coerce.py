"""Turning whatever a settings file holds into a value the app can use.

A settings file is somebody else's input -- hand-edited, written by an older
build, or synced from another machine -- so every field read out of one goes
through a coercion whose contract is: **never raise, and never return something
that does more work than the listener asked for.** A file with a typo in it
behaves like a file with nothing in it, never like a crash.

Extracted from ``models_settings`` under GATE-11 (extract, never rebaseline).
That module is the settings *record*, which gains a field every few days; this is
the handful of functions that read one, which change almost never. The split is
along the line the two things actually grow at.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = ["coerce_float", "normalize_alert_mode", "normalize_boost_level", "one_of"]


def one_of(value: object, allowed: set[str], default: str) -> str:
    """*value* when it is one of *allowed*, else *default*.

    The default is always the safe direction: never a mode that does more work
    than the listener chose.
    """
    wanted = str(value or "").strip().lower()
    return wanted if wanted in allowed else default


def coerce_float(value: object, default: float) -> float:
    """*value* as a float, or *default*.

    ``bool`` is rejected explicitly because it is an ``int`` in Python, and a
    stored ``true`` becoming ``1.0`` is a speed of 1x arriving from a field that
    never held a speed.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value) if value.strip() else default
        except ValueError:
            return default
    return default


def normalize_alert_mode(value: object) -> str:
    """A stored new-episode alert mode, through the one shared normalisation."""
    from quill.core.podcasts.episode_alerts import normalize_alert

    return normalize_alert(value)


def normalize_boost_level(value: object) -> str:
    """A stored Volume Boost level, through the one shared normalisation."""
    from quill.core.podcasts.volume_boost import normalize

    return normalize(value)
