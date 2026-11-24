"""What each app counts as "the moment that matters" (FUX-15).

Each function returns the probes for one app: callables answering ``""`` when
that work is idle, or the end of "... waits until <phrase>" while it is busy
(see :mod:`quill.core.maintenance_moment`). They read state the app already
keeps and add none. :func:`probes_for` picks the app's set by its key.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.maintenance_moment import Probe

__all__ = [
    "BROADCAST_ENDS",
    "DICTATION_ENDS",
    "PLAYBACK_STOPS",
    "READ_ALOUD_STOPS",
    "RECORDING_ENDS",
    "WORK_FINISHES",
    "probes_for",
]

DICTATION_ENDS = "dictation ends"
READ_ALOUD_STOPS = "reading aloud stops"


def _windows_dictation() -> str:
    from quill.ui.windows_dictation_commands import dictation_active

    return DICTATION_ENDS if dictation_active() else ""


def _quill(host: Any) -> list[Probe]:
    def locked_dictation() -> str:
        controller = getattr(host, "_live_dictation", None)
        return DICTATION_ENDS if controller is not None and controller.is_busy else ""

    def read_aloud() -> str:
        reader = getattr(host, "_read_aloud", None)
        return READ_ALOUD_STOPS if getattr(reader, "state", "") == "playing" else ""

    return [locked_dictation, _windows_dictation, read_aloud]


def _lite(_host: Any) -> list[Probe]:
    return [_windows_dictation]


RECORDING_ENDS = "the recording ends"
PLAYBACK_STOPS = "playback stops"
BROADCAST_ENDS = "the live broadcast ends"
WORK_FINISHES = "the work in progress finishes"


def _radio(host: Any) -> list[Probe]:
    def recording() -> str:
        recorder = getattr(host, "_radio_recorder", None)
        return RECORDING_ENDS if recorder is not None and recorder.is_recording else ""

    def playing() -> str:
        from quill.ui.radio.playback_state import RadioPlayerState

        controller = getattr(host, "_radio_controller", None)
        if controller is None:
            return ""
        audible = {
            RadioPlayerState.CONNECTING,
            RadioPlayerState.BUFFERING,
            RadioPlayerState.PLAYING,
            RadioPlayerState.RECONNECTING,
        }
        return PLAYBACK_STOPS if controller.state.state in audible else ""

    return [recording, playing]


def _cast(host: Any) -> list[Probe]:
    def playing() -> str:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        controller = getattr(host, "_podcast_controller", None)
        if controller is None:
            return ""
        # Loading counts: the episode is about to be heard (and between
        # auto-advanced episodes the engine briefly reports not playing).
        audible = {PodcastPlayerState.LOADING, PodcastPlayerState.PLAYING}
        busy = controller.is_playing() or controller.state.state in audible
        return PLAYBACK_STOPS if busy else ""

    return [playing]


def _studio(host: Any) -> list[Probe]:
    def broadcasting() -> str:
        live = getattr(host, "_live", None) is not None or getattr(host, "_live_starting", False)
        return BROADCAST_ENDS if live else ""

    def recording() -> str:
        busy = (
            getattr(host, "_demo", None) is not None
            or bool(getattr(host, "_demo_busy", ""))
            or bool(getattr(host, "_capture_pending", False))
        )
        return RECORDING_ENDS if busy else ""

    def working() -> str:
        return WORK_FINISHES if getattr(host, "_protected_background_jobs", None) else ""

    def playing() -> str:
        player = getattr(host, "_active_player", None)
        is_playing = getattr(player, "is_playing", None)
        return PLAYBACK_STOPS if callable(is_playing) and is_playing() else ""

    return [broadcasting, recording, working, playing]


_BY_APP: dict[str, Callable[[Any], list[Probe]]] = {
    "quill": _quill,
    "quilllite": _lite,
    "radio": _radio,
    "cast": _cast,
    "studio": _studio,
}


def probes_for(app_key: str, host: Any) -> list[Probe]:
    """*host*'s probes; an app with none listed has only the shared rules."""
    build = _BY_APP.get(app_key)
    return build(host) if build is not None else []
