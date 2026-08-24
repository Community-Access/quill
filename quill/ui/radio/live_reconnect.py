"""Getting a dropped live station back, instead of announcing that it stopped.

Extracted from ``player_controller.py`` rather than grown inside it -- that
module is at its GATE-11 ceiling and this is a self-contained concern with one
input (the controller) and one job. Same shape as
:mod:`quill.ui.radio.resume_playback` and :mod:`quill.ui.radio.bounded_playback_ui`:
plain functions taking the controller as ``host``, so the three "this is what
happens to a stream" modules read alike.

**The bug this exists for** (reported by John, 2026-08-13; the investigation is
in Quill Radio's 3.0 release notes). iHeart serves its stations as HLS with a
three-segment window -- thirty seconds of audio -- behind a per-listener
redirect and a five-second access token, topped up every ten seconds. If a
*single* playlist refresh or segment fetch fails, the already-buffered audio
keeps playing for twenty to thirty seconds and then runs out. mpv reports EOF,
the controller read EOF on a live station as "the stream ended", and the
listener heard "Stopped" with no explanation and no way back except playing the
station again by hand.

Two layers answer that, and both are needed:

* **ffmpeg reconnects the read.** ``mpv_radio_engine._STREAM_LAVF_OPTIONS``
  makes a transient failure self-heal below the player, which is where the
  great majority of these belong -- nothing is announced because nothing was
  lost.
* **This module reconnects the stream**, for when the first layer has already
  given up and the connection is genuinely gone. It is deliberately the second
  line and not the first.

Four rules it must not break:

* **A recording that ends has ended.** EOF on a bounded source -- a finished
  YouTube video, a LibriVox chapter, an Archive episode -- is the real end of
  the thing, and reconnecting would replay it. Only a *live* station reconnects.
* **It is bounded, and it says so.** Three attempts with a widening delay, each
  announced with its number, then the honest stop. A player that retries
  silently forever is indistinguishable from one that has hung.
* **It never fights the listener.** Stop, or playing something else, moves the
  controller's play token on, and a retry whose token is stale is dropped
  rather than hijacking whatever is playing now.
* **It never announces success it did not have.** The reconnect is reported as
  attempted; "Reconnected" is only said once the engine actually loads.
"""

from __future__ import annotations

from typing import Any

#: How many times a dropped live station is retried before Quill Radio stops
#: and says so. Three is enough to ride out a router blip or an iHeart token
#: refresh that missed, and short enough that a station taken off the air is
#: reported within half a minute rather than retried into the evening.
MAX_ATTEMPTS = 3

#: Delay before each attempt, in milliseconds, widening as attempts fail.
#: The first is short because most drops are momentary; the last is long
#: enough to let a server that is restarting come back.
BACKOFF_MS: tuple[int, ...] = (2_000, 5_000, 15_000)


def _attempts(host: Any) -> int:
    return int(getattr(host, "_live_reconnect_attempts", 0))


def reset(host: Any) -> None:
    """Forget the attempt count. Called whenever a stream successfully loads."""
    host._live_reconnect_attempts = 0


def _is_bounded(host: Any) -> bool:
    """Whether what just finished had an end of its own.

    Asked of the controller's public seam rather than the engine directly, so
    the answer is the same one the transport keys off -- a source that declared
    itself a recording is bounded even on an engine that cannot measure it.
    """
    probe = getattr(host, "is_seekable", None)
    if probe is not None:
        try:
            return bool(probe())
        except Exception:  # pragma: no cover - a partially built host
            return False
    return False


def handle_finished(host: Any) -> bool:
    """React to the engine reporting EOF. True when a retry was scheduled.

    The caller (``PlayerController._on_finished``) stops and announces only
    when this returns False, so the two outcomes stay in one place: either a
    reconnect is now in flight and the listener has been told, or the stream is
    genuinely over.
    """
    # Lazy, and from the controller: RadioPlayerState is defined there, and
    # the controller reaches this module the same way, so neither import is
    # taken at module scope and the pair cannot deadlock on each other.
    from quill.ui.radio.playback_state import RadioPlayerState

    station = getattr(getattr(host, "_state", None), "station", None)
    if station is None:
        return False
    if _is_bounded(host):
        # A recording reaching its end is not a fault. Keep the place first, so
        # "finished" and "stopped here" cannot disagree.
        return False

    attempt = _attempts(host) + 1
    if attempt > MAX_ATTEMPTS:
        reset(host)
        return False
    host._live_reconnect_attempts = attempt

    name = getattr(station, "display_name", "") or "the station"
    # RECONNECTING rather than CONNECTING. Both are true of the wire; only one
    # is true of the listener. "Connecting" is what a station somebody just
    # chose does, and a listener who pressed nothing deserves to hear that the
    # app is recovering rather than starting -- which is also why the sentence
    # composed here is now the one the status line renders, instead of being
    # written into a field nothing read.
    host._set_state(
        RadioPlayerState.RECONNECTING,
        message=f"Reconnecting to {name}. Attempt {attempt} of {MAX_ATTEMPTS}.",
    )
    delay = BACKOFF_MS[min(attempt - 1, len(BACKOFF_MS) - 1)]
    token = int(getattr(host, "_play_token", 0))
    _schedule(host, delay, lambda: _retry(host, token))
    return True


def _schedule(host: Any, delay_ms: int, work: Any) -> None:
    """Run *work* on the UI thread after *delay_ms*.

    Through the host so this module stays wx-free and a test can drive the
    retry synchronously by supplying its own ``_schedule_later``.
    """
    scheduler = getattr(host, "_schedule_later", None)
    if scheduler is None:  # pragma: no cover - every real controller has one
        work()
        return
    scheduler(delay_ms, work)


def _retry(host: Any, token: int) -> None:
    """Load the station again, unless the listener has moved on."""
    # Lazy, and from the controller: RadioPlayerState is defined there, and
    # the controller reaches this module the same way, so neither import is
    # taken at module scope and the pair cannot deadlock on each other.
    from quill.ui.radio.playback_state import RadioPlayerState

    if int(getattr(host, "_play_token", 0)) != token:
        # Stop, or another station, happened while this retry was waiting.
        return
    station = getattr(getattr(host, "_state", None), "station", None)
    if station is None:
        return

    url = host._resolve_playback_url(station)
    if url and host._engine.load(url):
        # Loading is not yet playing: _on_loaded announces the recovery and
        # clears the counter, so nothing here claims a success it cannot see.
        return
    if _attempts(host) >= MAX_ATTEMPTS:
        reset(host)
        name = getattr(station, "display_name", "") or "That station"
        # A drop that outlasted every retry is exactly the failure worth a
        # second look an hour later, so it is written down as well as said
        # (11.5) -- with the station's address as the handle Retry needs.
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        problem_log.record_problem(
            app_data_dir(),
            problem_log.KIND_STREAM,
            name,
            f"dropped and could not be reconnected after {MAX_ATTEMPTS} attempts",
            target=str(getattr(station, "stream_url", "") or ""),
        )
        host._set_state(
            RadioPlayerState.STOPPED,
            message=(
                f"{name} could not be reconnected after {MAX_ATTEMPTS} attempts. "
                "It may be off the air."
            ),
        )
        return
    # Still have attempts left: fall back through the same door, which
    # announces the next attempt and schedules it.
    handle_finished(host)


def announce_recovery(host: Any) -> str:
    """The message for a load that followed a reconnect, or "".

    Kept here so ``_on_loaded`` does not have to know how reconnects are
    counted -- it asks for the words and clears the state in one call.
    """
    if _attempts(host) <= 0:
        return ""
    reset(host)
    station = getattr(getattr(host, "_state", None), "station", None)
    name = getattr(station, "display_name", "") or "the station"
    return f"Reconnected to {name}."
