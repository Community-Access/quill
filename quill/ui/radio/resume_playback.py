"""Resuming a recording where you stopped.

Extracted from ``player_controller.py`` rather than grown inside it: that module
is at its GATE-11 ceiling, and this is a self-contained concern with one input
(the controller) and one job.

Same shape as :mod:`quill.ui.radio.bounded_playback_ui` -- plain functions taking
the controller as ``host`` -- so the two halves of "this thing has a timeline"
read alike.

The rule underneath all of it: **a live station has no position worth
remembering.** You tune in and you are where everyone else is. A recording is the
opposite, and losing your place in a four-hour chapter is the difference between
a library and a shelf you cannot reach. Which one you have is
``RadioStation.is_recording``, declared by the source that produced the row.

wx-free: this touches the controller and the store, never a widget.
"""

from __future__ import annotations

from typing import Any

#: Built once per process. The store itself is cheap, but creating it touches
#: the data directory, which a controller assembled in a test has no business
#: doing merely by existing.
_STORE: Any = None


def _store() -> Any:
    global _STORE
    if _STORE is None:
        from quill.core.radio.resume import ResumeStore

        _STORE = ResumeStore()
    return _STORE


def set_store_for_tests(store: Any) -> None:
    """Point the module at a store in a temporary directory."""
    global _STORE
    _STORE = store


def is_recording(station: object | None) -> bool:
    """Whether *station* is a finished recording rather than a live stream."""
    return bool(station is not None and getattr(station, "is_recording", False))


def saved_position_ms(station: object | None) -> int:
    """Where *station* was left, or 0.

    Never raises: a profile that cannot be read should cost you your place, not
    your playback.
    """
    if not is_recording(station):
        return 0
    try:
        point = _store().position_for(getattr(station, "stream_url", ""))
    except Exception:  # noqa: BLE001 - a lost position is not a lost stream
        return 0
    return point.position_ms if point is not None else 0


def remember(host: Any) -> None:
    """Save where the current recording reached.

    Called before playback leaves it -- on Stop, and when switching to another
    station -- because once the engine has moved on there is no position left to
    read.
    """
    state = getattr(host, "_state", None)
    station = getattr(state, "station", None)
    if not is_recording(station):
        return
    try:
        if not host.is_seekable():
            return
        _store().remember(
            getattr(station, "stream_url", ""),
            int(host.position_ms()),
            duration_ms=int(host.duration_ms()),
            # The station's own name, so the recording can be listed in
            # Continue Listening rather than only recognised if it is opened
            # again -- the stored key is a normalised identity and says
            # nothing a person could read.
            label=str(getattr(station, "name", "") or ""),
        )
    except Exception:  # noqa: BLE001 - best effort, never fatal
        return


def forget(host: Any, station: object | None = None) -> None:
    """Start this recording from the beginning next time."""
    target = (
        station if station is not None else getattr(getattr(host, "_state", None), "station", None)
    )
    if target is None:
        return
    try:
        _store().forget(getattr(target, "stream_url", ""))
    except Exception:  # noqa: BLE001
        return


#: The settings values this understands, in the order a settings list shows
#: them. Anything else falls back to "spoken" rather than going quiet, because
#: a mis-set preference should never silently remove information.
VERBOSITIES: tuple[tuple[str, str], ...] = (
    ("spoken", "Say where it is resuming from"),
    ("brief", "Just say it is resuming"),
    ("silent", "Say nothing"),
)


def announcement(position_ms: int, *, verbosity: str = "spoken") -> str:
    """What to say when a recording resumes (pure).

    Three settings, because this is a judgement about somebody else's ears:

    * ``spoken`` -- "Resuming at 12 minutes 8 seconds." The default. A recording
      that silently starts twenty minutes in is disorienting if you had
      forgotten you were part-way through it.
    * ``brief`` -- "Resuming." For someone who wants the fact and not the number.
    * ``silent`` -- nothing at all, for someone who finds any of it chatter.

    Returns ``""`` when there is nothing to say, so the caller can announce
    unconditionally and never emit an empty utterance.
    """
    if position_ms <= 0:
        return ""
    if verbosity == "silent":
        return ""
    if verbosity == "brief":
        return "Resuming."
    from quill.core.radio.resume import spoken_resume

    return f"Resuming at {spoken_resume(position_ms)}."
