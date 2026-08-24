"""Choosing which audio you hear, and which captions come with it.

Extracted from ``player_controller.py`` under GATE-11 (extract, never
rebaseline), and a genuine concern rather than a slice: everything here answers
*which rendition of this video am I listening to*, which is a different question
from how it is played.

It exists for **described audio**. A video's described track is a second
narration mixed into the programme that says what a sighted viewer can see, and
almost no desktop player surfaces it usefully -- where they expose it at all it
is a numbered list a blind listener has to choose from by playing each in turn.
:mod:`quill.core.radio.audio_tracks` names them instead; this is what plays the
one you chose.

The one thing worth knowing about the mechanics: **a rendition is a different
URL, not a channel inside one stream.** Selecting one is therefore a reload, the
same shape as the cross-engine switch -- and the position is carried across,
because losing your place in a two-hour film to switch to the described narration
would make the feature unusable in exactly the case it matters most.
"""

from __future__ import annotations

from typing import Any


def audio_tracks(host: Any) -> list[Any]:
    """Every selectable audio rendition of what is playing.

    Captured on the resolve at no extra cost, exactly like the chapters and the
    captions -- the same single request answers with all of it.
    """
    stream = host._youtube_stream
    if stream is None:
        return []
    return list(getattr(stream, "audio_tracks", ()) or ())


def caption_track(host: Any) -> tuple[str, bool]:
    """``(caption url, is automatic)`` for what is playing, or ``("", False)``."""
    stream = host._youtube_stream
    if stream is None:
        return "", False
    return (
        str(getattr(stream, "caption_url", "") or ""),
        bool(getattr(stream, "caption_is_automatic", False)),
    )


def selected_audio_track(host: Any) -> Any:
    """The rendition currently playing, or ``None`` when it is the default."""
    return getattr(host, "_selected_audio_track", None)


def play_audio_track(host: Any, track: Any) -> bool:
    """Switch to *track*. True when playback moved to it.

    Through the controller's ordinary play path, **not** straight into the
    engine. Loading the rendition's URL directly was the shorter route and it
    quietly skipped everything that path does: it left Sound Enhancements
    pointing at the previous rendition (the relay is built per URL, so the
    listener either lost their enhancement or kept hearing the old track
    through a relay nobody stopped), it skipped the volume and speed the
    station is due, and it lost the one cross-engine rescue and the spoken
    error that every other failed load gets. Switching to described audio and
    hearing the ordinary track -- or nothing -- was the report (2026-08-23).

    ``_play_resolved_station`` clears the chosen track by design (a *new*
    station has no rendition chosen yet), so the choice is recorded after it
    rather than before.
    """
    from quill.ui.radio.playback_state import RadioPlayerState

    station = host._state.station
    url = str(getattr(track, "stream_url", "") or "")
    if station is None or not url:
        return False
    resume_at = host.position_ms() if host.is_seekable() else 0
    previous_override = host._playback_url_override
    previous_track = host._selected_audio_track
    host._playback_url_override = url
    host._play_resolved_station(station)
    if host._state.state is RadioPlayerState.ERROR:
        # The old rendition is still the one the listener had, so the old
        # answers must stay true: leaving the failed URL as the override would
        # hand it to the next reconnect, and the picker would claim a track
        # that never loaded.
        host._playback_url_override = previous_override
        host._selected_audio_track = previous_track
        return False
    host._selected_audio_track = track
    if resume_at > 0:
        # Put them back where they were. The reload starts at zero otherwise,
        # and "switch to described audio" would cost you your place every time.
        host._pending_resume_ms = resume_at
    return True


def described_available(host: Any) -> Any:
    """The described rendition of what is playing, or ``None``."""
    from quill.core.radio.audio_tracks import described_track

    return described_track(audio_tracks(host))


#: Said once, when a video that carries described audio starts playing. The
#: feature announcing itself, because the alternative is that it only helps the
#: people who already know it exists -- and those are the last people who need
#: telling. Once per station, never repeated, and never interrupting: it rides
#: the ordinary announcement path like everything else.
DESCRIBED_AVAILABLE = (
    "Described audio is available for this video. "
    "Press Ctrl+Alt+D to hear the narration of what is on screen."
)


def announce_described_if_new(host: Any) -> bool:
    """Tell the listener once that this video has a described track.

    True when it said something. ``host`` is the frame; the "once" is keyed on
    the station, so switching away and back does not repeat it within a session
    and a genuinely new video does get its own announcement.
    """
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return False
    described = described_available(controller)
    if described is None:
        return False
    station = getattr(getattr(controller, "state", None), "station", None)
    key = getattr(station, "stream_url", "") or getattr(station, "name", "")
    if not key or key in getattr(host, "_described_announced", ()):
        return False
    seen = set(getattr(host, "_described_announced", set()))
    seen.add(key)
    host._described_announced = seen
    host._announce(DESCRIBED_AVAILABLE)
    return True
