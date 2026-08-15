"""Pausing and rewinding live radio -- the buffer, and moving inside it.

Extracted from ``player_controller.py`` under GATE-11 (extract, never
rebaseline). One concern: a live stream has no timeline, but the mpv engine
keeps a rolling demuxer cache of what has already arrived, and that cache is a
timeline of sorts -- roughly forty-five minutes of it. Everything here is about
moving within that window and reporting honestly how far behind the live edge
you now are.

Two things it will not do, both deliberate:

* **It never invents a position.** On the classic Windows Media engine there is
  no cache to move inside, so every function here answers ``None`` and the
  caller says why rather than reporting a made-up number. That distinction is
  the whole reason these return ``None`` instead of ``0``.
* **Back to Live prefers a seek and falls back to a reconnect.** Some streams'
  caches cannot say where the live edge is; a fresh connection always can,
  because a fresh connection *is* live.
"""

from __future__ import annotations

from typing import Any


def rewind(host: Any, seconds: int = 30) -> float | None:
    """Jump back within the live buffer.

    Returns how far behind live playback now is, in seconds, or ``None`` when
    that is unavailable -- the classic engine, or nothing playing. The caller
    announces either way.
    """
    return seek(host, -abs(seconds))


def forward(host: Any, seconds: int = 30) -> float | None:
    """Jump forward toward the live edge, after a rewind."""
    return seek(host, abs(seconds))


def seek(host: Any, seconds: int) -> float | None:
    """Move *seconds* within the buffer. ``None`` when there is no buffer."""
    if not host._is_mpv_active():
        return None
    engine = host._mpv_engine
    if engine is None or not engine.seek_relative(float(seconds)):
        return None
    return engine.behind_live_seconds()


def jump_to_live(host: Any) -> bool:
    """Return to the live edge. False when nothing is playing."""
    from quill.ui.radio.player_controller import RadioPlayerState

    station = host._state.station
    if station is None or host._state.state is RadioPlayerState.STOPPED:
        return False
    if host._is_mpv_active() and host._mpv_engine is not None and host._mpv_engine.jump_to_live():
        return True
    # No usable cache position: reconnect, which lands on the live edge by
    # definition.
    host.play_station(station)
    return True


def behind_live_seconds(host: Any) -> float | None:
    """How far behind the live edge playback is, or ``None`` when unknown."""
    if not host._is_mpv_active() or host._mpv_engine is None:
        return None
    return host._mpv_engine.behind_live_seconds()


def engine_track_title(host: Any) -> str:
    """The engine's own idea of the current track, or "".

    mpv's ``media-title``: the fallback for What's Playing when the
    out-of-band ICY tap gets nothing, which is every HLS stream and a good many
    others. Here because it is the same "ask the engine about the live stream"
    question as the rest of this module, and never worth an exception -- a title
    we cannot read is simply a title we do not have.
    """
    if not host._is_mpv_active() or host._mpv_engine is None:
        return ""
    try:
        return str(host._mpv_engine.now_playing_title())
    except Exception:  # noqa: BLE001
        return ""
