"""Which backend plays this station, and what to do when it will not.

Extracted from ``player_controller.py`` for the same reason
:mod:`quill.ui.radio.resume_playback` and :mod:`quill.ui.radio.live_reconnect`
were: that module is at its GATE-11 ceiling, and GATE-11 says *extract*, not
rebaseline. Same shape as those two -- plain functions taking the controller as
``host`` -- so every "what happens to a stream" concern reads alike and none of
them is a second class hiding inside the first.

The two decisions here are genuinely one concern, which is why they moved
together:

* :func:`select` picks the engine **before** a load, from the listener's
  preference plus what is actually installed plus which output device they
  asked for.
* :func:`attempt_fallback` picks the *other* engine **after** a load has
  failed, once per play attempt. WMP cannot decode Ogg Vorbis, Opus or HLS at
  all, and mpv occasionally misbehaves where WMP is fine, so each rescues the
  other. Once per attempt matters: two engines that each fall back to the other
  without a latch is an infinite loop with audio.

Deliberately unchanged in the move: every log line, the spoken output-device
and missing-mpv messages, and the rule that a Spotify station selects the
Spotify engine outright and skips the mpv/wx logic entirely, because its audio
is DRM-bound to that SDK and no other backend can play it.
"""

from __future__ import annotations

import logging
from typing import Any

from quill.ui.radio.mpv_radio_engine import MpvRadioEngine, mpv_output_device_available

_log = logging.getLogger(__name__)


def select(host: Any) -> None:
    """Point ``host._engine`` at the backend this station needs.

    "auto" prefers mpv whenever libmpv is present -- that is what delivers
    device routing, live pause/rewind, Volume Boost, and Ogg/Opus/HLS stations
    to everyone once libmpv ships in the app. "wx" is the classic escape hatch;
    "mpv" insists, with a spoken fallback when it is absent. A chosen output
    device also pulls in mpv, since no other backend can route one.
    """
    # Spotify stations play only on the Spotify engine (DRM via the SDK).
    if host._is_spotify_station(host._state.station):
        spotify = host._ensure_spotify_engine()
        if spotify is not None:
            if host._engine is not spotify:
                host._engine.close()
                host._engine = spotify
            return
        # No token source (not signed in): fall through so load() fails with
        # the Spotify-specific error rather than silently doing nothing.
    # Leaving a Spotify station: close the Spotify engine before choosing a
    # stream backend below (never leave it as the active engine).
    elif host._spotify_engine is not None and host._engine is host._spotify_engine:
        host._engine.close()
        host._spotify_engine = None
        host._engine = host._wx_engine

    mpv_present = mpv_output_device_available()
    if host._playback_engine == "wx":
        wanted_mpv = False
    elif host._playback_engine == "mpv":
        wanted_mpv = mpv_present
    else:  # auto
        wanted_mpv = mpv_present
    # #5 observability: why a given backend was chosen for this station.
    _log.debug(
        "Radio engine selection: preference=%s, mpv_present=%s -> %s",
        host._playback_engine,
        mpv_present,
        "mpv" if wanted_mpv else "wx.media",
    )

    if wanted_mpv:
        if host._mpv_engine is None:
            _build_mpv(host)
        else:
            try:
                host._mpv_engine.set_audio_device(host._output_device)
            except Exception:  # noqa: BLE001
                _log.exception("audio-device switch failed")
    if wanted_mpv and host._mpv_engine is not None:
        if host._engine is not host._mpv_engine:
            host._engine.close()
            host._engine = host._mpv_engine
        return

    if host._on_output_device_error is not None:
        if bool(host._output_device) and host._playback_engine != "wx":
            host._on_output_device_error(
                "The chosen radio output device could not be used; playing "
                "through the system default instead."
            )
        elif host._playback_engine == "mpv":
            host._on_output_device_error(
                "The mpv playback engine is not available; using Windows Media instead."
            )
    # Switch away only from the mpv engine (never from a test-injected fake):
    # in production the engine is always one of the two.
    if host._mpv_engine is not None and host._engine is host._mpv_engine:
        host._engine.close()
        host._engine = host._wx_engine


def _build_mpv(host: Any) -> bool:
    """Construct the mpv engine on *host*, or leave it None. True on success.

    One constructor call rather than the two near-identical copies the two
    callers used to carry -- the pair drifting apart is how one path ends up
    without the buffering callback and a stalled stream goes quiet with no
    announcement.
    """
    try:
        host._mpv_engine = MpvRadioEngine(
            host._parent,
            on_loaded=host._on_loaded,
            on_finished=host._on_finished,
            on_error=host._on_error,
            audio_device=host._output_device,
            on_buffering=host._on_buffering,
        )
    except Exception:  # noqa: BLE001 - fall back, never fail playback
        _log.exception("mpv radio engine unavailable; using wx.media")
        return False
    return True


def attempt_fallback(host: Any) -> bool:
    """Retry the current station on the other backend. True when a retry began.

    One rescue per play attempt, latched on ``host._fallback_attempted``.
    """
    from quill.ui.radio.player_controller import RadioPlayerState

    station = host._state.station
    if host._fallback_attempted or station is None:
        return False
    host._fallback_attempted = True

    if host._is_mpv_active():
        target = host._wx_engine
    elif mpv_output_device_available():
        if host._mpv_engine is None and not _build_mpv(host):
            return False
        target = host._mpv_engine
    else:
        return False

    _log.info("Retrying stream on the %s engine", "wx" if target is host._wx_engine else "mpv")
    host._engine.close()
    host._engine = target
    host._engine.set_volume(host._effective_volume())
    host._set_state(RadioPlayerState.CONNECTING, message="")
    url = host._resolve_playback_url(station)
    return bool(host._engine.load(url))
