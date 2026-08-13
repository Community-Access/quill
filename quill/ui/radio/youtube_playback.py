"""The asynchronous half of playing a YouTube station (#1268).

A YouTube link is a web page, and turning it into audio is a network round trip
through yt-dlp. That cannot happen on the UI thread: a frozen window is unusable
with a screen reader, and the freeze would land exactly when the listener
pressed Play. So the resolve runs on a worker thread and its result is applied
back on the UI thread.

This module holds that machinery so :mod:`quill.ui.radio.player_controller`
keeps its shape -- it owns playback, not concurrency plumbing. The controller
passes itself in; these functions only touch its documented playback surface
(``_state``, ``_set_state``, ``_play_resolved_station``, ``_playback_url_override``,
``_play_token``).

The token is the whole safety story: every play and every stop bumps it, so a
resolve that lands after the listener stopped, or after they picked a different
station, is dropped instead of hijacking playback.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

import wx

from quill.core.radio.models import RadioStation

if TYPE_CHECKING:  # pragma: no cover - typing only
    from quill.ui.radio.player_controller import RadioPlayerController

#: Spoken when the host wired no resolver at all (YouTube support unavailable).
NO_RESOLVER_MESSAGE = "YouTube links need the yt-dlp component, which is not available."

#: Spoken when a resolve fails without a reason of its own.
GENERIC_FAILURE_MESSAGE = "That YouTube link could not be opened."


def is_youtube_station(station: RadioStation | None) -> bool:
    """True when *station* is a YouTube link needing a resolve before it plays."""
    if station is None:
        return False
    from quill.core.radio.youtube import is_youtube_url

    return is_youtube_url(station.stream_url)


def begin_youtube_play(
    controller: RadioPlayerController, station: RadioStation, *, token: int
) -> None:
    """Announce CONNECTING, then resolve *station* on a worker thread.

    With no resolver injected the station errors cleanly rather than handing an
    HTML page to the audio engine, which would fail with a meaningless message.
    """
    resolver = controller._resolve_youtube  # noqa: SLF001 - documented seam
    state = controller._state  # noqa: SLF001
    from quill.ui.radio.player_controller import RadioPlayerState

    if resolver is None:
        state.station = station
        controller._set_state(RadioPlayerState.ERROR, message=NO_RESOLVER_MESSAGE)  # noqa: SLF001
        return
    state.station = station
    controller._set_state(RadioPlayerState.CONNECTING, message="")  # noqa: SLF001

    def work() -> None:
        stream: Any = None
        try:
            answer = resolver(station.stream_url)
            error = ""
            # The resolver may hand back either a plain URL or the whole
            # YouTubeStream. The richer form is what carries the video's
            # length and chapters, which is how a finished video is told
            # apart from a live broadcast -- see apply_youtube_result.
            if isinstance(answer, str):
                resolved = answer
            else:
                stream = answer
                resolved = str(getattr(answer, "stream_url", "") or "")
        except Exception as exc:  # noqa: BLE001 - reported, never raised on a thread
            resolved, error = "", str(exc)
        wx.CallAfter(apply_youtube_result, controller, station, token, resolved, error, stream)

    threading.Thread(target=work, name="quill-youtube-resolve", daemon=True).start()


def apply_youtube_result(
    controller: Any,
    station: RadioStation,
    token: int,
    resolved: str,
    error: str,
    stream: Any = None,
) -> None:
    """UI-thread continuation of :func:`begin_youtube_play`."""
    from quill.ui.radio.player_controller import RadioPlayerState

    if token != controller._play_token:  # noqa: SLF001 - stale resolve, listener moved on
        return
    if not resolved:
        controller._set_state(  # noqa: SLF001
            RadioPlayerState.ERROR, message=error or GENERIC_FAILURE_MESSAGE
        )
        return
    controller._playback_url_override = resolved  # noqa: SLF001
    # Hand the controller the video's own facts before playback starts, so the
    # engine can be told it is holding a finished recording rather than a
    # broadcast. A live YouTube stream reports no duration and so arrives here
    # looking exactly like an ordinary station, which is correct.
    controller._youtube_stream = stream  # noqa: SLF001
    controller._play_resolved_station(station)  # noqa: SLF001
