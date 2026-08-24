"""Speed and skip-silence for the things Quill Radio plays that are *not* live.

QUILL Cast has had both for years, per podcast, and the engine underneath
Quill Radio has had both all along -- ``audio_enhance.build_filter_graph``
grew its Smart Speed clause with a comment saying "podcasts only; radio
callers never pass ``smart_speed_enabled=True``". Nobody ever taught Radio to
pass it, and nobody taught it to remember a speed for anything that was not a
podcast episode. So a recording of a two-hour programme played at 1x with
every pause in it, and the 1.5x you chose for it last night was gone by
morning (list.md 11.7).

This module is the wx-free half of closing that: *which kind of bounded thing
is playing*, and *what speed that kind should play at*. The engine work is
one boolean handed to a filter graph that already exists.

**Per kind, not per row.** A podcast is remembered per show because shows have
voices and hosts you have an opinion about. A recording is not: what somebody
means by "1.5x for recordings" is every recording, and asking them to set it
again for each captured hour would be the same feature with the cost moved
onto them. Live radio is excluded entirely -- a broadcast plays at broadcast
speed, and there is nothing to skip in it that has not already gone out.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "KIND_LIVE",
    "KIND_OTHER",
    "KIND_PODCAST",
    "KIND_RECORDING",
    "KIND_YOUTUBE",
    "SPEED_MAX",
    "SPEED_MIN",
    "clamp_speed",
    "describe_skip_silence",
    "kind_for",
    "remembers_speed",
    "speed_for_kind",
]

KIND_RECORDING = "recording"
KIND_YOUTUBE = "youtube"
KIND_PODCAST = "podcast"
KIND_LIVE = "live"
KIND_OTHER = "other"

#: mpv's usable range, the same clamp ``set_playback_rate`` applies.
SPEED_MIN = 0.25
SPEED_MAX = 4.0

#: Station ``source`` values that name a saved recording of a broadcast.
_RECORDING_SOURCES = frozenset({"Recording", "Recordings", "Radio Recordings"})

#: ...and the ones that name a YouTube row.
_YOUTUBE_SOURCES = frozenset({"YouTube", "YouTube Channel", "YouTube Playlist"})


def kind_for(station: Any) -> str:
    """Which kind of thing *station* is, for speed and skip-silence purposes.

    Reads the row's own ``source`` and, for a recording, the fact that its
    address is a local file -- a recording reached from the Recordings window
    carries no directory source at all, and a local path is the one thing that
    can never be a live broadcast.
    """
    if station is None:
        return KIND_OTHER
    source = str(getattr(station, "source", "") or "").strip()
    from quill.core.podcasts.radio_listens import PODCAST_EPISODE_SOURCES

    if source in PODCAST_EPISODE_SOURCES:
        return KIND_PODCAST
    if source in _YOUTUBE_SOURCES:
        return KIND_YOUTUBE
    if source in _RECORDING_SOURCES:
        return KIND_RECORDING
    url = str(getattr(station, "stream_url", "") or "")
    if url and not url.lower().startswith(("http://", "https://", "rtsp://", "mms://")):
        # A local file: a recording, an imported audiobook chapter, something
        # dragged in. Bounded by construction, so it gets the recording rules.
        return KIND_RECORDING
    if getattr(station, "is_recording", False):
        return KIND_RECORDING
    return KIND_LIVE


def remembers_speed(kind: str) -> bool:
    """Whether a speed chosen while this kind plays should be remembered here.

    Podcasts are remembered per show elsewhere (``radio_listens``), and live
    radio has no speed at all, so this is exactly the pair 11.7 adds.
    """
    return kind in (KIND_RECORDING, KIND_YOUTUBE)


def clamp_speed(rate: float) -> float:
    """*rate* inside mpv's usable range."""
    try:
        value = float(rate)
    except (TypeError, ValueError):
        return 1.0
    return max(SPEED_MIN, min(SPEED_MAX, value))


def speed_for_kind(history: Any, kind: str) -> float:
    """The remembered speed for *kind* (1.0 when there is none)."""
    if kind == KIND_RECORDING:
        return clamp_speed(getattr(history, "recording_speed", 1.0) or 1.0)
    if kind == KIND_YOUTUBE:
        return clamp_speed(getattr(history, "youtube_speed", 1.0) or 1.0)
    return 1.0


def set_speed_for_kind(history: Any, kind: str, rate: float) -> bool:
    """Remember *rate* for *kind*. False when this kind is not remembered."""
    if not remembers_speed(kind):
        return False
    value = clamp_speed(rate)
    if kind == KIND_RECORDING:
        history.recording_speed = value
    else:
        history.youtube_speed = value
    return True


def describe_skip_silence(enabled: bool, kind: str) -> str:
    """What to say when Skip Silence is toggled, including when it will not
    apply to what is playing right now.

    Saying only "Skip Silence on" while a live station plays would be true and
    misleading: the setting took, and nothing changed, and there is no way to
    tell those apart by ear.
    """
    state = "on" if enabled else "off"
    if kind == KIND_LIVE:
        return (
            f"Skip Silence {state}. It has no effect on live radio, which plays "
            "at broadcast speed; it applies to recordings, YouTube rows and "
            "podcast episodes."
        )
    if not enabled:
        return "Skip Silence off. Pauses play at their full length again."
    return "Skip Silence on. Long pauses are shortened as this plays."


def speed_sentence(rate: float, kind: str) -> str:
    """The tail a speed change adds when the choice is being remembered."""
    if not remembers_speed(kind):
        return ""
    noun = "recordings" if kind == KIND_RECORDING else "YouTube rows"
    if rate == 1.0:
        return f" {noun.capitalize()} will play at normal speed."
    return f" Remembered for {noun}."
