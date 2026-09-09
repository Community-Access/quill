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
    # The per-podcast settings work gave three more things a lesson can watch
    # for. All three are library facts rather than window facts, which is what
    # makes them answerable at all: the settings windows are modal, so a check
    # about "is the dialog open" could never fire while somebody was in it.
    "filter-saved": "a podcast now has an Episode Filter",
    "settings-changed": "a podcast now answers a setting for itself",
    "labels-grew": "a podcast now has a label",
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


def _library(host: Any) -> Any:
    return getattr(host, "_podcast_library", None)


def _counted(host: Any, attribute: str) -> int | None:
    """How many entries one of the library's per-podcast maps holds.

    ``None`` when the library is not up yet, which the shared probe reads as
    "cannot tell" rather than as "no". A lesson that fired its check because
    the library had not loaded would be worse than one that never fired.
    """
    holder = getattr(_library(host), attribute, None)
    try:
        return len(holder) if holder is not None else None
    except TypeError:
        return None


def _active_filters(host: Any) -> int | None:
    """Podcasts whose filter actually decides something.

    Counted by ``is_active`` rather than by the map's length, because a filter
    that has been written but switched off changes nothing -- and a lesson
    that congratulated somebody for saving one would be lying.
    """
    library = _library(host)
    shows = getattr(library, "shows", None)
    if library is None or shows is None:
        return None
    try:
        from quill.core.podcasts.episode_filter_maintenance import is_active

        return sum(1 for show in shows if is_active(library, show))
    except Exception:  # noqa: BLE001 - a half-built library is not an error here
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


def _grew(before: int | None, now: int | None) -> bool:
    """Whether a count went up since the lesson took its baseline.

    Both readings must be real numbers. A check compared against a ``None``
    baseline would fire the first time the library became readable, which
    reads as a lesson congratulating you for something you did not do.
    """
    return before is not None and now is not None and now > before


class CastProbe:
    """Cast's :class:`~quill.ui.tutorial_checks.CheckProbe`."""

    def known(self) -> frozenset[str]:
        return frozenset(_CHECKS)

    def snapshot(self, host: Any) -> dict[str, Any]:
        return {
            "state": _state_name(host),
            "shows": _show_count(host),
            "queue": _queue_length(host),
            "filters": _active_filters(host),
            "overrides": _counted(host, "scope_overrides"),
            "labels": _counted(host, "show_labels"),
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
            return (_grew(baseline.get("shows"), _show_count(host)), said)
        if check == "filter-saved":
            return (_grew(baseline.get("filters"), _active_filters(host)), said)
        if check == "settings-changed":
            return (_grew(baseline.get("overrides"), _counted(host, "scope_overrides")), said)
        if check == "labels-grew":
            return (_grew(baseline.get("labels"), _counted(host, "show_labels")), said)
        # queue-grew
        return (_grew(baseline.get("queue"), _queue_length(host)), said)


#: The one instance; it holds no state of its own.
PROBE = CastProbe()
