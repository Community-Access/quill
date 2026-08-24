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


#: Spoken when a *resolved* YouTube stream is refused by the audio engine.
#: YouTube's stream addresses are issued per player client and stop working
#: for everyone else; when the yt-dlp component falls behind, the resolve still
#: succeeds -- title, length and all -- and the address it hands back is dead
#: on arrival (a 403 from googlevideo). The player then looked like it had hung
#: on "connecting", with no way to tell that the fix is one menu item away.
STALE_COMPONENT_MESSAGE = (
    "YouTube refused the stream address. That usually means the YouTube support "
    "component is out of date: use Station, then Update YouTube Support, and try again."
)


def playback_failure_message(station: RadioStation | None, message: str) -> str:
    """The failure sentence a listener can act on (pure).

    A YouTube station that fails *after* its resolve succeeded is almost never
    the network and never the station: it is the component. Everything else
    keeps the engine's own words.
    """
    if not is_youtube_station(station):
        return message
    return f"{STALE_COMPONENT_MESSAGE} ({message})" if message else STALE_COMPONENT_MESSAGE


def consent_granted(controller: Any) -> bool:
    """Whether YouTube may be contacted for this play (asks once, ever).

    Asked on the UI thread, before the resolve starts. It used to be asked only
    by Add Custom Station, so every other way to reach a YouTube row -- a
    followed channel's uploads, a saved video, a favorite, a search result --
    refused at play time with a message naming a dialog the listener was not
    in (reported 2026-08-23).

    Only from the UI thread: an auto-advance or a queue step can reach
    ``play_station`` off-thread, and a modal question there would be a hang.
    Off-thread the answer is "carry on", and the resolver's own consent guard
    reports it cleanly instead.
    """
    ask = controller._youtube_consent  # noqa: SLF001 - documented seam
    if ask is None or not wx.IsMainThread():
        return True
    try:
        return bool(ask())
    except Exception:  # noqa: BLE001 - a failed ask must never block playback
        return True


def begin_youtube_play(
    controller: RadioPlayerController, station: RadioStation, *, token: int
) -> None:
    """Announce CONNECTING, then resolve *station* on a worker thread.

    With no resolver injected the station errors cleanly rather than handing an
    HTML page to the audio engine, which would fail with a meaningless message.
    """
    resolver = controller._resolve_youtube  # noqa: SLF001 - documented seam
    state = controller._state  # noqa: SLF001
    from quill.ui.radio.playback_state import RadioPlayerState

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

    threading.Thread(  # GATE-40-OK: one-shot yt-dlp resolve; CallAfter applies, stale
        # results are dropped by the token check.
        target=work,
        name="quill-youtube-resolve",
        daemon=True,
    ).start()


def apply_youtube_result(
    controller: Any,
    station: RadioStation,
    token: int,
    resolved: str,
    error: str,
    stream: Any = None,
) -> None:
    """UI-thread continuation of :func:`begin_youtube_play`."""
    from quill.ui.radio.playback_state import RadioPlayerState

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
