"""MusicBrainz: what else is known about the song a station just played.

Quill Radio already records artist and title for every song it hears
(``core/radio/song_history.py``). MusicBrainz turns that pair into the release it
came from, the year, and how long it runs -- which is the difference between a
history list and a history you can do something with.

Keyless, and it stays that way: MusicBrainz asks for a **descriptive
User-Agent** identifying the application and a contact, and enforces **one
request per second**. Both are honoured here, the second by an interval this
module keeps for itself rather than trusting every caller to remember.

Three rules, because enrichment must never become a cost:

* **Strictly opt-in**, and off by default.
* **Never blocking playback.** This is called from history, on a worker, after
  the fact. A song plays whether or not MusicBrainz answers.
* **Degrades to nothing.** No match, a timeout, a rate limit: the entry keeps
  exactly the artist and title it already had. An enrichment that can fail loudly
  is worse than no enrichment.

One reviewed egress site (:func:`_fetch`), HTTPS-only over a verified TLS
context, Safe Mode gated, results cached. wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache

#: MusicBrainz asks that the agent identify the application *and* offer a way to
#: get in touch. This is not politeness -- an anonymous agent is blocked.
_USER_AGENT = f"QUILL-Radio/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 2_000_000
_ENDPOINT = "https://musicbrainz.org/ws/2/recording"

#: Their documented limit is one request per second, sustained. Kept here rather
#: than in each caller so nobody can forget it.
MIN_INTERVAL_SECONDS = 1.1
_last_request = 0.0

#: A song's facts do not change. A month is conservative.
_MAX_AGE_SECONDS = 30 * 24 * 3600


class MusicBrainzError(CodedError):
    """A MusicBrainz lookup failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-MUSICBRAINZ-LOOKUP"


@dataclass(frozen=True, slots=True)
class RecordingFacts:
    """What MusicBrainz knows about one recording."""

    title: str = ""
    artist: str = ""
    release: str = ""
    year: str = ""
    length_ms: int = 0

    @property
    def is_empty(self) -> bool:
        return not (self.release or self.year or self.length_ms)

    @property
    def spoken_detail(self) -> str:
        """The extra facts as a listener hears them, or ``""`` (pure).

        Returns nothing at all when nothing was found, so the caller can append
        it unconditionally without ever announcing an empty clause.
        """
        parts = []
        if self.release:
            parts.append(f"from {self.release}")
        if self.year:
            parts.append(self.year)
        if self.length_ms >= 1000:
            seconds = self.length_ms // 1000
            minutes, seconds = divmod(seconds, 60)
            parts.append(
                f"{minutes} minutes {seconds} seconds" if minutes else f"{seconds} seconds"
            )
        return ", ".join(parts)


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`MusicBrainzError` when Safe Mode is active."""
    if safe_mode:
        raise MusicBrainzError(
            "Song details are disabled in Safe Mode. Restart QUILL normally to look them up."
        )


def _throttle() -> None:
    """Hold to one request per second, globally."""
    global _last_request
    wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _fetch(url: str) -> str:
    """One HTTPS GET of MusicBrainz -- the reviewed egress site, rate-limited."""
    _throttle()
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
    except (
        urllib.error.URLError,
        TimeoutError,
        ssl.SSLError,
        OSError,
        http.client.HTTPException,
    ) as error:
        raise MusicBrainzError(f"Could not reach MusicBrainz: {error}") from error
    return payload.decode("utf-8", errors="replace")


def parse_recording(json_text: str) -> RecordingFacts:
    """The best match from a recording search (pure).

    "Best" is simply the first, because MusicBrainz already ranks by its own
    score and second-guessing that from here would be worse. A result whose
    score is poor is still returned -- the caller decides whether to use it,
    and :attr:`RecordingFacts.is_empty` is the honest signal.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return RecordingFacts()
    recordings = data.get("recordings") if isinstance(data, dict) else None
    if not isinstance(recordings, list) or not recordings:
        return RecordingFacts()
    first = recordings[0]
    if not isinstance(first, dict):
        return RecordingFacts()
    artist = ""
    for credit in first.get("artist-credit", []) or []:
        if isinstance(credit, dict):
            name = credit.get("name") or (credit.get("artist") or {}).get("name")
            if name:
                artist = str(name).strip()
                break
    release, year = "", ""
    for entry in first.get("releases", []) or []:
        if not isinstance(entry, dict):
            continue
        release = str(entry.get("title", "") or "").strip()
        date = str(entry.get("date", "") or "").strip()
        year = date[:4] if len(date) >= 4 and date[:4].isdigit() else ""
        if release:
            break
    length = first.get("length")
    return RecordingFacts(
        title=str(first.get("title", "") or "").strip(),
        artist=artist,
        release=release,
        year=year,
        length_ms=int(length) if isinstance(length, int) else 0,
    )


def lookup(artist: str, title: str, *, safe_mode: bool = False) -> RecordingFacts:
    """What MusicBrainz knows about *artist* -- *title*.

    Empty facts for no match, a hiccup, or a blank input: this enriches a song
    history entry and must never be the reason one fails to appear.
    """
    refuse_in_safe_mode(safe_mode)
    artist, title = (artist or "").strip(), (title or "").strip()
    if not artist or not title:
        return RecordingFacts()
    query = f'artist:"{artist}" AND recording:"{title}"'
    url = f"{_ENDPOINT}?{urllib.parse.urlencode({'query': query, 'fmt': 'json', 'limit': 1})}"
    payload, _age = directory_cache.resolve(
        f"musicbrainz:{artist.casefold()}{title.casefold()}",
        lambda: _as_json(parse_recording(_fetch(url))),
        max_age_seconds=_MAX_AGE_SECONDS,
        empty={},
    )
    return _from_json(payload)


def _as_json(facts: RecordingFacts) -> dict:
    return {
        "title": facts.title,
        "artist": facts.artist,
        "release": facts.release,
        "year": facts.year,
        "length_ms": facts.length_ms,
    }


def _from_json(payload: object) -> RecordingFacts:
    if not isinstance(payload, dict):
        return RecordingFacts()
    return RecordingFacts(
        title=str(payload.get("title", "")),
        artist=str(payload.get("artist", "")),
        release=str(payload.get("release", "")),
        year=str(payload.get("year", "")),
        length_ms=int(payload.get("length_ms") or 0),
    )
