"""Quill Radio's reviewed call sites for scrobbling and AudD song recognition.

Beside :mod:`quill.tools.network_egress_entries_radio` rather than inside it,
because that module is near its GATE-11 ceiling. Both features are ideas from
BlindRadio by serrebidev (MIT); both are off until the listener turns them on
and supplies their own sign-in or token.
"""

from __future__ import annotations

RADIO_LISTENING_EGRESS: dict[str, str] = {
    "core/radio/scrobble_http.py::post": (
        "Single egress site for scrobbling (core/radio/listenbrainz.py, "
        "core/radio/lastfm.py). Destinations are fixed in code: "
        "api.listenbrainz.org submit-listens, ws.audioscrobbler.com/2.0 and "
        "libre.fm/2.0. Sends the artist, title and album of a song the "
        "listener heard for at least a minute and the time they started hearing "
        "it (track.scrobble, submit-listens single/import), or of the song just "
        "started (track.updateNowPlaying, playing_now), plus the listener's own "
        "ListenBrainz user token or last.fm/Libre.fm session key and the app's "
        "API key with an MD5 signature; during sign-in, auth.getToken and "
        "auth.getSession with the token the listener approved in their browser. "
        "Never the station, never audio, never anything else about the listener. "
        "OFF BY DEFAULT: reached only after the listener checks Send the songs I "
        "hear to <service> in Preferences and pastes a token or signs in, or "
        "presses Sign In; runs on the task manager, never the UI thread; failed "
        "scrobbles wait in a capped on-disk queue with backoff. HTTPS-only (any "
        "other scheme refused) over a verified TLS context with a bounded timeout "
        "and answer size; refused in Safe Mode."
    ),
    "core/radio/audd.py::_post": (
        "Single egress site for AudD song recognition: one multipart POST to "
        "api.audd.io carrying the listener's own AudD API token and about twenty "
        "seconds of the audio already playing, cut from the playback buffer "
        "(never a new connection to the station). Returns artist, title and "
        "album, or no match. ONLY ON REQUEST: reached solely from Identify This "
        "Song when the listener has chosen AudD as the Song recognition service "
        "in Preferences (AcoustID is the default) and pasted a token; there is no "
        "automatic recognition. The sample is capped at AudD's 10 MB limit and "
        "deleted after the request. HTTPS-only over a verified TLS context with "
        "a bounded timeout and answer size; refused in Safe Mode."
    ),
}


__all__ = ["RADIO_LISTENING_EGRESS"]
