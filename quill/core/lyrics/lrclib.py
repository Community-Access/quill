"""LRCLIB: the words of a song, plain or timed, on request.

`LRCLIB <https://lrclib.net>`_ is a free, keyless community catalogue of song
lyrics. Its server is MIT-licensed, its database is published as public dumps,
and it exists to give free music players synchronised lyrics. It answers two
questions:

* ``GET /api/search?track_name=&artist_name=`` -- ranked candidates. Quill
  Radio's path: a broadcast gives an artist and a title and nothing else.
* ``GET /api/get?track_name=&artist_name=&album_name=&duration=`` -- the one
  exact match, or 404. Quill Media Player's path: a file has its own album tag
  and a real length, so it can ask for the right cut, not a live version.

Each answer carries ``plainLyrics`` (newline-separated text), ``syncedLyrics``
(LRC, one ``[mm:ss.xx]`` line per lyric) and ``instrumental`` -- a real answer
("this track has no words"), which is a different fact from "nothing found".

**Consent.** Nothing here runs by itself. A lookup happens only when somebody
opens the Lyrics window or asks for lyrics, never in the background, never per
song as titles change, and never in Safe Mode (:func:`refuse_in_safe_mode`).

**Etiquette LRCLIB asks for, kept here rather than trusted to callers:** a
descriptive User-Agent naming the app, its version and its homepage
(``http_client.user_agent``); requests spaced at least
:data:`MIN_INTERVAL_SECONDS` apart, globally; an identical lookup never asked
twice (the cache below); and a ``429`` honoured through its ``Retry-After``
once, up to :data:`_MAX_RETRY_AFTER_SECONDS`, then given up -- never a loop.

**Not found is not an error.** A ``404`` returns an empty :class:`Lyrics`.
:class:`LyricsError` is for an unreachable network and for the Safe Mode
refusal, nothing else: an optional lookup that raised on "no match" would fail
loudly for the most ordinary answer it has.

**The cache lives in memory, for this session only** (:data:`CACHE_ON_DISK`).
This is a deliberate divergence from ``core/radio/musicbrainz.py``, which caches
through ``directory_cache`` on disk for a month: release years are facts about
a recording, but lyrics are publishers' copyrighted text, and a growing private
corpus of them in ``%APPDATA%`` -- a record of what somebody listened to -- is a
step further than showing the words on request, for no benefit anyone has asked
for. Do not "fix" this by reaching for ``directory_cache`` without that decision.

One reviewed egress site (:func:`_fetch`): HTTPS only, through
``quill.core.net``'s verified TLS context, bounded timeout and size.
wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context

__all__ = [
    "CACHE_ON_DISK",
    "MIN_INTERVAL_SECONDS",
    "LrcLine",
    "Lyrics",
    "LyricsError",
    "clear_cache",
    "get_exact",
    "line_at",
    "parse_lrc",
    "parse_response",
    "refuse_in_safe_mode",
    "search",
]

#: Where looked-up lyrics are kept. **A default awaiting Jeff's decision**
#: (xradio1.md section 9, 2026-10-15): False keeps them in memory for this
#: session only, so nothing about what somebody listened to is written to disk,
#: and that is the conservative choice. True caches them on disk through
#: ``core/radio/directory_cache.py`` for :data:`_DISK_MAX_AGE_SECONDS`, like
#: MusicBrainz. Change it here and nowhere else.
CACHE_ON_DISK = False

_ENDPOINT = "https://lrclib.net/api"
#: LRCLIB asks for requests spaced about a quarter of a second apart.
MIN_INTERVAL_SECONDS = 0.25
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 2_000_000
#: The longest a ``Retry-After`` is waited out, once. Longer means "not now".
_MAX_RETRY_AFTER_SECONDS = 5.0
#: How many lookups the session cache holds. A song is re-observed five or six
#: times a track on the radio, so the cache is load-bearing; a session's worth
#: of songs is plenty and the oldest go first.
_CACHE_SIZE = 200
_DISK_MAX_AGE_SECONDS = 30 * 24 * 3600

_last_request = 0.0
_cache: OrderedDict[str, Lyrics] = OrderedDict()


class LyricsError(CodedError):
    """A lyrics lookup could not be made (network unreachable, or Safe Mode)."""

    code = "QUILL-LYRICS-LRCLIB-LOOKUP"


@dataclass(frozen=True, slots=True)
class Lyrics:
    """What LRCLIB knows about one song's words. Every field may be empty."""

    track: str = ""
    artist: str = ""
    album: str = ""
    duration_seconds: float = 0.0
    instrumental: bool = False
    plain: str = ""
    #: Raw LRC, unparsed; see :func:`parse_lrc`.
    synced: str = ""

    @property
    def is_empty(self) -> bool:
        """True when there are no words and no instrumental answer either."""
        return not (self.instrumental or self.plain.strip() or self.synced.strip())

    @property
    def has_synced(self) -> bool:
        return bool(parse_lrc(self.synced))

    @property
    def text(self) -> str:
        """The words to show: the plain text, or the timed words without times."""
        if self.plain.strip():
            return self.plain.strip()
        return "\n".join(line.text for line in parse_lrc(self.synced)).strip()


@dataclass(frozen=True, slots=True)
class LrcLine:
    """One timed lyric line."""

    start_ms: int
    text: str


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`LyricsError` when Safe Mode is active."""
    if safe_mode:
        raise LyricsError("Lyrics are disabled in Safe Mode. Restart normally to look them up.")


def clear_cache() -> None:
    """Forget every lookup this session made (tests, and nothing else)."""
    _cache.clear()


# -- pure ----------------------------------------------------------------------

_TIMESTAMP_RE = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")


def parse_lrc(synced: str) -> tuple[LrcLine, ...]:
    """The timed lines of an LRC text, in time order (pure, never raises).

    Two- and three-digit fractions both read correctly (``.5``, ``.50`` and
    ``.500`` are all half a second); a line with several timestamps (a repeated
    chorus) yields one line per timestamp; blank lyric lines -- an instrumental
    break -- are kept, because they mark where the words stop. Tags such as
    ``[ar:...]`` and lines with no timestamp are ignored.
    """
    lines: list[LrcLine] = []
    for raw in (synced or "").splitlines():
        stamps = list(_TIMESTAMP_RE.finditer(raw))
        if not stamps or stamps[0].start() != 0:
            continue
        text = raw[stamps[-1].end() :].strip()
        for stamp in stamps:
            minutes, seconds, fraction = stamp.group(1), stamp.group(2), stamp.group(3) or ""
            fraction_ms = int((fraction + "00")[:3]) if fraction else 0
            start = (int(minutes) * 60 + int(seconds)) * 1000 + fraction_ms
            lines.append(LrcLine(start_ms=start, text=text))
    lines.sort(key=lambda line: line.start_ms)
    return tuple(lines)


def line_at(lines: Sequence[LrcLine], position_ms: int) -> int:
    """The index of the line being sung at *position_ms*, or ``-1`` before the first.

    The last line whose start is at or before the position (pure).
    """
    index = -1
    for i, line in enumerate(lines):
        if line.start_ms <= position_ms:
            index = i
        else:
            break
    return index


def _from_record(record: object) -> Lyrics:
    if not isinstance(record, dict):
        return Lyrics()
    try:
        duration = float(record.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    return Lyrics(
        track=str(record.get("trackName") or record.get("name") or "").strip(),
        artist=str(record.get("artistName") or "").strip(),
        album=str(record.get("albumName") or "").strip(),
        duration_seconds=duration,
        instrumental=bool(record.get("instrumental")),
        plain=str(record.get("plainLyrics") or ""),
        synced=str(record.get("syncedLyrics") or ""),
    )


def parse_response(json_text: str, *, prefer_synced: bool = False) -> Lyrics:
    """The best answer in an LRCLIB response body (pure, never raises).

    A ``/get`` body is one record; a ``/search`` body is a ranked list, from
    which the first record with words (timed words first, when
    *prefer_synced*) is taken, else the first instrumental. A ``404`` body
    (``{"name": "TrackNotFound", ...}``) and anything unreadable are empty.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return Lyrics()
    if isinstance(data, dict):
        if data.get("statusCode") or data.get("name") == "TrackNotFound":
            return Lyrics()
        return _from_record(data)
    if not isinstance(data, list):
        return Lyrics()
    found = [_from_record(record) for record in data]
    found = [lyrics for lyrics in found if not lyrics.is_empty]
    if prefer_synced:
        for lyrics in found:
            if lyrics.has_synced:
                return lyrics
    for lyrics in found:
        if lyrics.text:
            return lyrics
    return found[0] if found else Lyrics()


# -- network -------------------------------------------------------------------


def _throttle() -> None:
    """Hold every request at least :data:`MIN_INTERVAL_SECONDS` apart, globally."""
    global _last_request
    wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _retry_after(error: urllib.error.HTTPError) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers is not None else None
    try:
        seconds = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return seconds if 0 <= seconds <= _MAX_RETRY_AFTER_SECONDS else None


def _fetch(url: str) -> str:
    """One HTTPS GET of LRCLIB -- the reviewed egress site.

    Returns the response body, or ``""`` for "nothing here" (404, or a 429 that
    did not clear after one honoured ``Retry-After``). Raises
    :class:`LyricsError` only when LRCLIB cannot be reached at all.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": http_client.user_agent(), "Accept": "application/json"}
    )
    for attempt in (1, 2):
        _throttle()
        try:
            with urllib.request.urlopen(
                request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
            ) as resp:
                payload: bytes = resp.read(_MAX_BYTES)
            return payload.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt == 1:
                wait = _retry_after(error)
                if wait is not None:
                    time.sleep(wait)
                    continue
            if error.code in (404, 429):
                return ""
            raise LyricsError(f"LRCLIB answered {error.code}.") from error
        except (
            urllib.error.URLError,
            TimeoutError,
            ssl.SSLError,
            OSError,
            http.client.HTTPException,
        ) as error:
            raise LyricsError(f"Could not reach LRCLIB: {error}") from error
    return ""


def _cached(key: str, lookup: Callable[[], Lyrics]) -> Lyrics:
    """The session cache (or, if :data:`CACHE_ON_DISK`, the disk one)."""
    if CACHE_ON_DISK:
        from quill.core.radio import directory_cache

        payload, _age = directory_cache.resolve(
            f"lrclib:{key}",
            lambda: _as_json(lookup()),
            max_age_seconds=_DISK_MAX_AGE_SECONDS,
            empty={},
        )
        return _from_record(payload)
    hit = _cache.get(key)
    if hit is not None:
        _cache.move_to_end(key)
        return hit
    found = lookup()
    _cache[key] = found
    while len(_cache) > _CACHE_SIZE:
        _cache.popitem(last=False)
    return found


def _as_json(lyrics: Lyrics) -> dict[str, object]:
    return {
        "trackName": lyrics.track,
        "artistName": lyrics.artist,
        "albumName": lyrics.album,
        "duration": lyrics.duration_seconds,
        "instrumental": lyrics.instrumental,
        "plainLyrics": lyrics.plain,
        "syncedLyrics": lyrics.synced,
    }


def search(artist: str, title: str, *, safe_mode: bool = False) -> Lyrics:
    """The words of *title* by *artist*, from LRCLIB's ranked search.

    Empty for a blank input or no match; raises :class:`LyricsError` only for
    Safe Mode or an unreachable network.
    """
    refuse_in_safe_mode(safe_mode)
    artist, title = (artist or "").strip(), (title or "").strip()
    if not title:
        return Lyrics()
    query = {"track_name": title}
    if artist:
        query["artist_name"] = artist
    url = f"{_ENDPOINT}/search?{urllib.parse.urlencode(query)}"
    key = f"search\x1f{artist.casefold()}\x1f{title.casefold()}"
    return _cached(key, lambda: parse_response(_fetch(url)))


def get_exact(
    artist: str,
    title: str,
    album: str,
    duration_seconds: float,
    *,
    safe_mode: bool = False,
) -> Lyrics:
    """The words of one exact recording, timed ones preferred.

    LRCLIB's exact lookup needs all four facts. When the file lacks an album or
    a length, or the exact lookup finds nothing, the ranked search answers
    instead -- preferring a result with timed words.
    """
    refuse_in_safe_mode(safe_mode)
    artist, title, album = (artist or "").strip(), (title or "").strip(), (album or "").strip()
    if not title:
        return Lyrics()
    seconds = max(0, round(float(duration_seconds or 0)))
    key = f"get\x1f{artist.casefold()}\x1f{title.casefold()}\x1f{album.casefold()}\x1f{seconds}"

    def lookup() -> Lyrics:
        if artist and album and seconds:
            query = {
                "artist_name": artist,
                "track_name": title,
                "album_name": album,
                "duration": str(seconds),
            }
            exact = parse_response(_fetch(f"{_ENDPOINT}/get?{urllib.parse.urlencode(query)}"))
            if not exact.is_empty:
                return exact
        query = {"track_name": title}
        if artist:
            query["artist_name"] = artist
        body = _fetch(f"{_ENDPOINT}/search?{urllib.parse.urlencode(query)}")
        return parse_response(body, prefer_synced=True)

    return _cached(key, lookup)
