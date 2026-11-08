"""What the station says it played: a station's own published playlist.

Quill Radio's Song History is what Quill heard -- the titles the stream sent
while you were listening. Many stations also publish their own list of recent
songs, with the time each one started, through an open, keyless API. That list
covers the songs before you tuned in, and it is the station's own word rather
than our reading of a metadata block. This module finds that list from the
stream address alone, so it works for a station found in any directory.

Seven sources, each matched by **the stream's host and path, never by the
station's name** -- a name match would one day show one station's songs under
another's:

* **AzuraCast** -- any host serving ``/listen/<shortcode>/<file>``; asks
  ``https://<host>/api/nowplaying/<shortcode>`` (documented at
  docs.azuracast.com/en/developers/apis) and keeps the answer only when the
  station it describes has the same shortcode.
* **KEXP** -- its own stream hosts; ``api.kexp.org/v2/plays`` ordered newest
  first (without the ordering it can answer a stale list), airbreaks skipped.
* **BBC** -- the BBC's own stream hosts; the service id (``bbc_radio_two``) is in
  the stream path. The segments API answers 400 above ten rows, and gives times
  only as phrases ("3 Minutes Ago"), which are kept as phrases.
* **Radio Paradise** -- ``stream.radioparadise.com``; the channel number comes
  from :func:`quill.core.radio.radio_paradise.playlist_channel`.
* **Live365** -- ``streaming.live365.com/<id>``; the station record's
  ``current-track`` and ``last-played``. Live365's own ad breaks are skipped.
* **laut.fm** -- ``stream.laut.fm/<name>``; ``api.laut.fm/station/<name>/last_songs``.
* **Triton Digital / StreamTheWorld** -- ``*.streamtheworld.com``; Triton's
  public now-playing history by mount name. A mount named for one encoding
  (``977_HITSAAC_SC``) usually files its titles under the plain name, so the
  trailing ``_SC`` and then ``AAC`` are stripped in turn until one answers.

The idea, the endpoint list and the edge cases (the KEXP ordering, the BBC row
limit, the Triton mount tip, the Radio Paradise channel table) come from
BlindRadio by serrebidev (MIT), crates/blindradio-core/src/sources/played.rs and
docs/radio-sources-research-2026-11-04.md. No code is copied; the parsing here
was written against live responses fetched for the purpose.

Every fetch is something the listener asked for (opening the station's
playlist), goes through the one reviewed egress site :func:`_fetch` -- HTTPS
only, a verified TLS context, a bounded timeout and size -- and is refused in
Safe Mode. wx-free, strict-typed.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.radio import live365, radio_paradise
from quill.core.radio.station_playlist_parsers import (
    PlayedSong,
    parse_azuracast,
    parse_bbc,
    parse_kexp,
    parse_laut_fm,
    parse_live365,
    parse_radio_paradise,
    parse_time,
    parse_triton,
)

__all__ = [
    "PROVIDER_AZURACAST",
    "PROVIDER_BBC",
    "PROVIDER_KEXP",
    "PROVIDER_LAUT_FM",
    "PROVIDER_LIVE365",
    "PROVIDER_RADIO_PARADISE",
    "PROVIDER_TRITON",
    "NO_PLAYLIST",
    "PlayedSong",
    "PlaylistSource",
    "StationPlaylist",
    "StationPlaylistError",
    "fetch_station_playlist",
    "match_source",
    "parse_azuracast",
    "parse_bbc",
    "parse_kexp",
    "parse_laut_fm",
    "parse_live365",
    "parse_radio_paradise",
    "parse_time",
    "parse_triton",
    "triton_mount_candidates",
]

PROVIDER_AZURACAST = "azuracast"
PROVIDER_KEXP = "kexp"
PROVIDER_BBC = "bbc"
PROVIDER_RADIO_PARADISE = "radio_paradise"
PROVIDER_LIVE365 = "live365"
PROVIDER_LAUT_FM = "laut_fm"
PROVIDER_TRITON = "triton"

#: What to say when a stream has no list this module can read. One sentence.
NO_PLAYLIST = "This station does not publish a playlist Quill Radio can read."

_TIMEOUT_SECONDS = 12.0
#: The largest answer here is KEXP's fifty plays, about 60 KB. Two megabytes is
#: generous and still stops a redirect to something that is not an API at all.
_MAX_BYTES = 2_000_000

#: Rows asked for. Triton returns no more than about fifty (three hours); the
#: BBC answers 400 above ten.
TRITON_ROWS = 50
KEXP_ROWS = 50
RADIO_PARADISE_ROWS = 50
BBC_ROWS = 10

#: Where each list came from, in words, for the window's provenance line.
_PROVIDER_NAMES: dict[str, str] = {
    PROVIDER_AZURACAST: "the station's own AzuraCast server",
    PROVIDER_KEXP: "KEXP",
    PROVIDER_BBC: "the BBC",
    PROVIDER_RADIO_PARADISE: "Radio Paradise",
    PROVIDER_LIVE365: "Live365",
    PROVIDER_LAUT_FM: "laut.fm",
    PROVIDER_TRITON: "Triton Digital, which streams the station",
}


class StationPlaylistError(CodedError):
    """A station-playlist request failed (network, unreadable reply, Safe Mode)."""

    code = "QUILL-RADIO-PLAYLIST-REQUEST"


@dataclass(frozen=True, slots=True)
class PlaylistSource:
    """Which published list a stream has, and the key that names the station."""

    provider: str
    #: Shortcode, service id, mount, station id or channel number, as text.
    key: str
    #: The AzuraCast server's own origin (``https://host``); empty otherwise.
    base: str = ""

    @property
    def name(self) -> str:
        """Who publishes the list, as a phrase ("KEXP", "the BBC")."""
        return _PROVIDER_NAMES.get(self.provider, "the station")

    def provenance(self) -> str:
        """The sentence the window shows above the list."""
        host = urllib.parse.urlsplit(self.api_urls()[0]).hostname or ""
        return (
            f"Published by {self.name}, at {host}. This is what the station says "
            "it played, not what Quill Radio heard."
        )

    def api_urls(self) -> tuple[str, ...]:
        """The URLs to ask, in order; the first that answers with songs wins."""
        quoted = urllib.parse.quote(self.key, safe="")
        if self.provider == PROVIDER_AZURACAST:
            return (f"{self.base}/api/nowplaying/{quoted}",)
        if self.provider == PROVIDER_KEXP:
            return (f"https://api.kexp.org/v2/plays/?limit={KEXP_ROWS}&ordering=-airdate",)
        if self.provider == PROVIDER_BBC:
            return (
                f"https://rms.api.bbc.co.uk/v2/services/{quoted}/segments/latest?limit={BBC_ROWS}",
            )
        if self.provider == PROVIDER_RADIO_PARADISE:
            return (
                "https://api.radioparadise.com/api/nowplaying_list_v2022"
                f"?chan={quoted}&list_num={RADIO_PARADISE_ROWS}",
            )
        if self.provider == PROVIDER_LIVE365:
            return (f"https://api.live365.com/station/{quoted}",)
        if self.provider == PROVIDER_LAUT_FM:
            return (f"https://api.laut.fm/station/{quoted}/last_songs",)
        if self.provider == PROVIDER_TRITON:
            return tuple(
                "https://np.tritondigital.com/public/nowplaying?"
                + urllib.parse.urlencode({
                    "mountName": mount,
                    "numberToFetch": TRITON_ROWS,
                    "eventType": "track",
                })
                for mount in triton_mount_candidates(self.key)
            )
        return ()


@dataclass(frozen=True, slots=True)
class StationPlaylist:
    """A station's published list, newest first, with where it came from."""

    source: PlaylistSource
    songs: tuple[PlayedSong, ...] = ()


# --- matching (pure) --------------------------------------------------------

_SAFE_KEY = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_TRITON_MOUNT = re.compile(r"^[A-Za-z0-9_]{2,60}$")
_BBC_SERVICE = re.compile(r"^bbc_[a-z0-9_]{2,60}$")
_LAUT_NAME = re.compile(r"^[a-z0-9_-]{1,60}$")
_KEXP_HOST = re.compile(r"^(?:kexp[a-z0-9-]*\.streamguys1\.com|live-[a-z0-9-]+\.kexp\.org)$")
_BBC_HOST = re.compile(
    r"^(?:as-hls-[a-z]{2}-live\.akamaized\.net|(?:[a-z0-9-]+\.)*bbci\.co\.uk"
    r"|(?:[a-z0-9-]+\.)*bbcmedia\.co\.uk)$"
)


def _stem(segment: str) -> str:
    return segment.split(".", 1)[0]


def match_source(stream_url: str) -> PlaylistSource | None:
    """The published list a stream address has, or None (pure).

    Decided by the address alone -- its host, and for AzuraCast its path shape
    -- and never by the station's name.
    """
    try:
        parts = urllib.parse.urlsplit(str(stream_url or "").strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not host:
        return None
    segments = [urllib.parse.unquote(s) for s in parts.path.split("/") if s]
    first = segments[0] if segments else ""

    if host == "streamtheworld.com" or host.endswith(".streamtheworld.com"):
        mount = _stem(segments[-1]) if segments else ""
        return PlaylistSource(PROVIDER_TRITON, mount) if _TRITON_MOUNT.match(mount) else None
    if host == "streaming.live365.com":
        station_id = live365.live365_station_id(stream_url)
        if station_id and first.lower() == station_id.lower():
            return PlaylistSource(PROVIDER_LIVE365, station_id.lower())
        return None
    if host == "stream.laut.fm" or host.endswith(".stream.laut.fm"):
        name = first.lower()
        return PlaylistSource(PROVIDER_LAUT_FM, name) if _LAUT_NAME.match(name) else None
    if _KEXP_HOST.match(host):
        return PlaylistSource(PROVIDER_KEXP, "kexp")
    if host == "stream.radioparadise.com":
        channel = radio_paradise.playlist_channel(stream_url)
        return None if channel is None else PlaylistSource(PROVIDER_RADIO_PARADISE, str(channel))
    if _BBC_HOST.match(host):
        for segment in segments:
            service = _stem(segment).split("-", 1)[0].lower()
            if _BBC_SERVICE.match(service):
                return PlaylistSource(PROVIDER_BBC, service)
        return None
    if len(segments) >= 3 and segments[0] == "listen" and _SAFE_KEY.match(segments[1]):
        # AzuraCast's own listen route. The API is asked over HTTPS whatever the
        # stream used; an explicit port is kept only when the stream was HTTPS
        # already, because an HTTP stream's port is the plain-text one.
        netloc = host if (port is None or parts.scheme == "http") else f"{host}:{port}"
        return PlaylistSource(PROVIDER_AZURACAST, segments[1], base=f"https://{netloc}")
    return None


def triton_mount_candidates(mount: str) -> tuple[str, ...]:
    """The mount names to try, in order: as given, then without ``_SC``, then
    without a trailing ``AAC`` (pure). BlindRadio found that 65 of 94
    StreamTheWorld stations answered once the encoding suffixes were gone."""
    bare = mount[:-3] if mount.upper().endswith("_SC") else mount
    plain = bare[:-3] if bare.upper().endswith("AAC") and len(bare) > 3 else bare
    out: list[str] = []
    for candidate in (mount, bare, plain):
        if candidate and candidate not in out:
            out.append(candidate)
    return tuple(out)


def _parse(source: PlaylistSource, payload: str, now: datetime | None) -> tuple[PlayedSong, ...]:
    if source.provider == PROVIDER_AZURACAST:
        return parse_azuracast(payload, source.key)
    if source.provider == PROVIDER_KEXP:
        return parse_kexp(payload)
    if source.provider == PROVIDER_BBC:
        return parse_bbc(payload, now=now)
    if source.provider == PROVIDER_RADIO_PARADISE:
        return parse_radio_paradise(payload)
    if source.provider == PROVIDER_LIVE365:
        return parse_live365(payload)
    if source.provider == PROVIDER_LAUT_FM:
        return parse_laut_fm(payload)
    if source.provider == PROVIDER_TRITON:
        return parse_triton(payload)
    return ()


# --- network ----------------------------------------------------------------


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`StationPlaylistError` when Safe Mode is active."""
    if safe_mode:
        raise StationPlaylistError(
            "Station playlists are off in Safe Mode. Restart Quill Radio normally to see them."
        )


def _fetch(url: str) -> str | None:
    """One HTTPS GET of a published playlist -- the single reviewed egress site.

    ``None`` for a 404 or 410: the station has no such list, which is an
    answer, not a failure. Any other failure raises.
    """
    if not url.startswith("https://"):
        raise StationPlaylistError("Only https:// playlist addresses are fetched.")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": http_client.user_agent(),
            "Accept": "application/json, application/xml;q=0.9, */*;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            data: bytes = resp.read(_MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code in (404, 410):
            return None
        raise StationPlaylistError(f"The playlist service answered {error.code}.") from error
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise StationPlaylistError(f"Could not reach the playlist service: {error}") from error
    if len(data) > _MAX_BYTES:
        raise StationPlaylistError("The playlist service sent far more than a playlist.")
    return data.decode("utf-8", errors="replace")


def fetch_station_playlist(
    stream_url: str,
    *,
    safe_mode: bool = False,
    now: datetime | None = None,
) -> StationPlaylist | None:
    """The station's own recent songs, newest first, or None when it has no list.

    ``None`` means the stream matches no source (say :data:`NO_PLAYLIST`); a
    :class:`StationPlaylist` with no songs means the source answered with
    nothing. Raises :class:`StationPlaylistError` for Safe Mode or a failure.
    Blocking: call it from the task manager, never the UI thread.
    """
    refuse_in_safe_mode(safe_mode)
    source = match_source(stream_url)
    if source is None:
        return None
    failure: StationPlaylistError | None = None
    answered = False
    for url in source.api_urls():
        try:
            payload = _fetch(url)
        except StationPlaylistError as error:
            failure = error
            continue
        answered = True  # an answer, even an empty one, is not a failure
        songs = _parse(source, payload or "", now)
        if songs:
            return StationPlaylist(source=source, songs=songs)
    if failure is not None and not answered:
        raise failure
    return StationPlaylist(source=source)
