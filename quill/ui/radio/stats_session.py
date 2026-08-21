"""The clock behind Listening Statistics: when Radio was actually playing.

One rule, and getting it right is the whole feature: **time only counts while
audio is coming out**. Not while a stream is connecting, not while it is
buffering through dead air, not while it is paused, and not while the app sits
stopped overnight. A statistics window that counts any of those is worse than
none, because it is confidently wrong about the one number it exists to report.

So this watches the same playback state changes everything else in Radio watches,
starts a clock on the transition *into* PLAYING, and flushes an accumulated
session when playback leaves PLAYING or moves to a different station.

**A flush on close, too.** The commonest way a listening session ends is the app
being closed while a station plays, and a session that only lands on a clean stop
would miss exactly the sessions that matter most.

Its own module because ``main_frame_radio`` is at its GATE-11 ceiling, and
because this is a real seam: everything here is about *elapsed time*, and none
of it touches the volume and history bookkeeping it sits beside.
"""

from __future__ import annotations

import time
from typing import Any

__all__ = ["flush", "on_state_changed"]

_STARTED = "_radio_stats_started"
_STATION = "_radio_stats_station"

#: Below this, a "session" is somebody skipping past a station in a list. Ten
#: seconds of a stream you rejected is not listening, and a log full of them
#: makes the per-station totals meaningless.
MIN_SESSION_SECONDS = 10.0


def _key(station: Any) -> str:
    from quill.core.radio.stats import station_key

    return station_key(station) if station is not None else ""


def flush(host: Any) -> float:
    """Record whatever has accumulated, and stop the clock. Returns the seconds.

    Never raises: statistics are a courtesy and one that failed must not cost
    somebody their playback.
    """
    started = getattr(host, _STARTED, None)
    station = getattr(host, _STATION, None)
    setattr(host, _STARTED, None)
    setattr(host, _STATION, None)
    # ``None``, not 0.0, is "no clock running": a monotonic clock is allowed to
    # read zero, and a falsy check would silently discard the session that
    # started at exactly that moment.
    if started is None or station is None:
        return 0.0
    seconds = max(0.0, time.monotonic() - float(started))
    if seconds < MIN_SESSION_SECONDS:
        return 0.0
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio import stats

        stats.record_listen(
            app_data_dir(),
            station,
            seconds,
            network=str(getattr(station, "source", "") or ""),
        )
    except Exception:  # noqa: BLE001 - statistics must never break playback
        return 0.0
    return seconds


def on_state_changed(host: Any, state: Any) -> None:
    """Start, keep or end the clock, according to what just happened."""
    try:
        playing = str(getattr(getattr(state, "state", None), "name", "")) == "PLAYING"
        station = getattr(state, "station", None)
        current = getattr(host, _STATION, None)

        if not playing:
            flush(host)
            return
        if current is not None and _key(current) == _key(station):
            # Still the same station, still playing: the clock keeps running.
            return
        # A different station started, or the first one did.
        flush(host)
        if station is not None and _key(station):
            setattr(host, _STARTED, time.monotonic())
            setattr(host, _STATION, station)
    except Exception:  # noqa: BLE001 - never break a state change over a stopwatch
        return
