"""Quill Radio's own answers to "did you do the step?".

The shared half -- peer windows, the probe protocol, the never-guess rule --
is :mod:`quill.ui.tutorial_checks`. This is the half only Radio can write:
what its playback controller, its favorites store and its recorder are doing
right now.

Every probe here reads a named attribute defensively and answers ``None`` when
it cannot see it. A controller that is not up yet, or an attribute a later
refactor renames, therefore produces a lesson that is merely quiet rather than
one that is stuck.
"""

from __future__ import annotations

from typing import Any

#: What a satisfied check says. Spoken, so written as a sentence: what changed,
#: in words somebody would use, and never "check passed".
_CHECKS: dict[str, str] = {
    "playing": "something is playing now",
    "paused": "it is paused",
    "muted": "the sound is muted",
    "volume-changed": "the volume moved",
    "favorite-added": "your favorites grew",
    "recording-started": "a recording is running",
    "recording-finished": "the recording finished",
}


def _controller_state(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return None
    try:
        return controller.state
    except Exception:  # noqa: BLE001 - a half-built controller is not an error here
        return None


def _state_name(host: Any) -> str:
    state = _controller_state(host)
    inner = getattr(state, "state", None)
    return str(getattr(inner, "name", ""))


def _volume(host: Any) -> int | None:
    value = getattr(_controller_state(host), "volume_percent", None)
    return int(value) if isinstance(value, int) else None


def _muted(host: Any) -> bool | None:
    value = getattr(_controller_state(host), "muted", None)
    return bool(value) if isinstance(value, bool) else None


def _favorite_count(host: Any) -> int | None:
    entries = getattr(getattr(host, "_radio_favorites", None), "favorites", None)
    try:
        return len(entries) if entries is not None else None
    except TypeError:
        return None


def _recording_count(host: Any) -> int | None:
    recorder = getattr(host, "_radio_recorder", None)
    if recorder is None:
        return None
    count = getattr(recorder, "active_count", None)
    if isinstance(count, int):
        return count
    flag = getattr(recorder, "is_recording", None)
    return int(bool(flag)) if isinstance(flag, bool) else None


class RadioProbe:
    """Radio's :class:`~quill.ui.tutorial_checks.CheckProbe`."""

    def known(self) -> frozenset[str]:
        return frozenset(_CHECKS)

    def snapshot(self, host: Any) -> dict[str, Any]:
        """What the app looked like when the step was shown.

        Deltas rather than absolutes wherever the question is "did you do it":
        somebody who already has forty favorites has not failed the step about
        adding one, and an absolute test would either pass instantly or never.
        """
        return {
            "state": _state_name(host),
            "volume": _volume(host),
            "muted": _muted(host),
            "favorites": _favorite_count(host),
            "recordings": _recording_count(host),
        }

    def answer(self, check: str, host: Any, baseline: dict[str, Any]) -> tuple[bool, str] | None:
        if check not in _CHECKS:
            return None
        said = _CHECKS[check]
        if check == "playing":
            return (_state_name(host) == "PLAYING", said)
        if check == "paused":
            return (_state_name(host) == "PAUSED", said)
        if check == "muted":
            return (bool(_muted(host)), said)
        if check == "volume-changed":
            before, now = baseline.get("volume"), _volume(host)
            return (before is not None and now is not None and now != before, said)
        if check == "favorite-added":
            before, now = baseline.get("favorites"), _favorite_count(host)
            return (before is not None and now is not None and now > before, said)
        if check == "recording-started":
            before, now = baseline.get("recordings"), _recording_count(host)
            return (before is not None and now is not None and now > before, said)
        # recording-finished
        before, now = baseline.get("recordings"), _recording_count(host)
        return (before is not None and now is not None and before > 0 and now < before, said)


#: The one instance; it holds no state of its own.
PROBE = RadioProbe()
