"""QUILL Cast's own answers to "did you do the step?".

The shared half -- peer windows, the probe protocol, the never-guess rule --
is :mod:`quill.ui.tutorial_checks`. Cast's own questions are about its player
and its library: is something playing, did you subscribe to something, did the
queue grow, did a download start.

Every probe reads a named attribute defensively and answers ``None`` when it
cannot see it, so a controller that is not up yet produces a lesson that is
merely quiet rather than one that is stuck.
"""

from __future__ import annotations

from typing import Any

_CHECKS: dict[str, str] = {
    "playing": "something is playing now",
    "paused": "it is paused",
    "subscriptions-grew": "you have a new subscription",
    "queue-grew": "the play queue grew",
}


def _state(host: Any) -> Any:
    controller = getattr(host, "_podcast_controller", None)
    if controller is None:
        return None
    try:
        return controller.state
    except Exception:  # noqa: BLE001 - a half-built controller is not an error here
        return None


def _state_name(host: Any) -> str:
    inner = getattr(_state(host), "state", None)
    return str(getattr(inner, "name", ""))


def _show_count(host: Any) -> int | None:
    shows = getattr(getattr(host, "_podcast_library", None), "shows", None)
    try:
        return len(shows) if shows is not None else None
    except TypeError:
        return None


def _queue_length(host: Any) -> int | None:
    """How many episodes are in the Play Queue, or None when it cannot be read."""
    for name in ("_podcast_queue", "_play_queue"):
        queue = getattr(host, name, None)
        if queue is None:
            continue
        entries = getattr(queue, "entries", None) or getattr(queue, "items", None)
        try:
            if entries is not None:
                return len(entries)
            return len(queue)
        except TypeError:
            continue
    return None


class CastProbe:
    """Cast's :class:`~quill.ui.tutorial_checks.CheckProbe`."""

    def known(self) -> frozenset[str]:
        return frozenset(_CHECKS)

    def snapshot(self, host: Any) -> dict[str, Any]:
        return {
            "state": _state_name(host),
            "shows": _show_count(host),
            "queue": _queue_length(host),
        }

    def answer(self, check: str, host: Any, baseline: dict[str, Any]) -> tuple[bool, str] | None:
        if check not in _CHECKS:
            return None
        said = _CHECKS[check]
        if check == "playing":
            return (_state_name(host) == "PLAYING", said)
        if check == "paused":
            return (_state_name(host) == "PAUSED", said)
        if check == "subscriptions-grew":
            before, now = baseline.get("shows"), _show_count(host)
            return (before is not None and now is not None and now > before, said)
        # queue-grew
        before, now = baseline.get("queue"), _queue_length(host)
        return (before is not None and now is not None and now > before, said)


#: The one instance; it holds no state of its own.
PROBE = CastProbe()
