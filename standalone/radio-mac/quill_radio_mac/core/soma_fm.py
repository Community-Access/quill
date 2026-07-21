"""SomaFM client: a free, keyless directory of curated, commercial-free
internet radio channels (https://somafm.com), blended into Internet Radio
search results alongside RadioBrowser.

Ported near-verbatim from upstream ``quill.core.radio.soma_fm``. Unlike
ACB Media's static list (:mod:`quill_radio_mac.core.acb_media`),
SomaFM's ~30-channel lineup is fetched live, but it is folded into the
*same* search results list as RadioBrowser -- no separate menu, no
visible "from SomaFM" label -- so it reads as one directory to the
user, not two.

Two egress calls: the channel list itself (``_http_json``), and -- only
for channels that match the user's search -- resolving that channel's
``.pls`` playlist to a real playable stream URL (``_http_text``), since
SomaFM's own JSON only ever links to playlist manifests, never a raw
stream. Both HTTPS-only with a verified TLS context, disabled in Safe
Mode via :func:`refuse_in_safe_mode`. wx-free, strict-typed.

Threading contract: pure parsing/ranking functions plus blocking
network calls (including a small thread pool for concurrent playlist
resolution); the UI calls :func:`search_stations` off the UI thread.

macOS notes: none -- fully platform-neutral.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from quill_radio_mac import __version__
from quill_radio_mac.core.error_codes import CodedError
from quill_radio_mac.core.models import RadioStation

_USER_AGENT = f"QuillRadioMac/{__version__}"
_CHANNELS_URL = "https://somafm.com/channels.json"
_TIMEOUT_SECONDS = 10.0
_MAX_RESOLVE_WORKERS = 8
_CATEGORY_TAG = "SomaFM"
#: Preferred playlist quality/format, in order -- highest-quality MP3 first,
#: falling back through the rest of what a channel actually publishes.
_QUALITY_ORDER = ("highest", "high", "low")
_FORMAT_ORDER = ("mp3", "aacp", "aac")
_PLS_FILE1_RE = re.compile(r"^\s*File1\s*=\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)


class SomaFmError(CodedError):
    """A SomaFM request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-SOMAFM-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`SomaFmError` when Safe Mode is active.

    Safe Mode disables every network service. Internet Radio is a
    network service, so the UI calls this before constructing a
    request. Kept in core (with the flag passed in) so the refusal is
    unit-testable without wx.
    """
    if safe_mode:
        raise SomaFmError(
            "Internet Radio is disabled in Safe Mode. "
            "Restart Quill Radio normally to browse or play stations."
        )


def _http_json(url: str) -> object:
    """One HTTPS GET returning decoded JSON -- a reviewed egress site."""
    import json

    payload = _http_text(url)
    if not payload:
        return []
    try:
        return json.loads(payload)
    except ValueError as error:
        raise SomaFmError("SomaFM returned an unreadable reply.") from error


def _http_text(url: str) -> str:
    """One HTTPS GET returning decoded text -- a reviewed egress site
    (shared by the channel list and per-channel playlist resolution)."""
    if not url.startswith("https://"):
        raise SomaFmError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            text: str = resp.read().decode("utf-8", errors="replace")
            return text
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise SomaFmError(f"Could not reach SomaFM: {error}") from error


def first_stream_url_from_pls(pls_text: str) -> str | None:
    """Pull ``File1=...`` out of a standard ``.pls`` playlist (pure).

    SomaFM's playlists list several mirror servers for the same stream;
    the first entry is as good as any -- the player's own reconnect
    handling covers a single mirror going away mid-stream.
    """
    match = _PLS_FILE1_RE.search(pls_text)
    return match.group(1).strip() if match else None


def _best_playlist(playlists: object) -> dict[str, object] | None:
    """Pick the best entry from a channel's ``playlists`` array (pure):
    prefers mp3 over aac variants, then highest quality over lower."""
    if not isinstance(playlists, list):
        return None
    entries = [p for p in playlists if isinstance(p, dict)]
    if not entries:
        return None

    def rank(entry: dict[str, object]) -> tuple[int, int]:
        fmt = str(entry.get("format", "")).lower()
        quality = str(entry.get("quality", "")).lower()
        fmt_rank = _FORMAT_ORDER.index(fmt) if fmt in _FORMAT_ORDER else len(_FORMAT_ORDER)
        quality_rank = (
            _QUALITY_ORDER.index(quality) if quality in _QUALITY_ORDER else len(_QUALITY_ORDER)
        )
        return (fmt_rank, quality_rank)

    return min(entries, key=rank)


def _channel_matches(channel: dict[str, object], query: str) -> bool:
    if not query:
        return True
    needle = query.strip().casefold()
    haystacks = (
        str(channel.get("title", "")),
        str(channel.get("description", "")),
        str(channel.get("genre", "")).replace("|", " "),
    )
    return any(needle in haystack.casefold() for haystack in haystacks)


def channels_from_json(data: object) -> list[dict[str, object]]:
    """Every channel entry from a parsed ``channels.json`` payload (pure;
    tolerant of junk)."""
    if not isinstance(data, dict):
        return []
    channels = data.get("channels")
    return [c for c in channels if isinstance(c, dict)] if isinstance(channels, list) else []


def _resolve_channel(channel: dict[str, object], *, safe_mode: bool) -> RadioStation | None:
    """Turn one matched channel into a playable :class:`RadioStation` by
    resolving its best playlist's ``.pls`` manifest. Returns ``None`` on
    any failure (missing fields, unreachable playlist, unparsable ``.pls``)
    so one bad channel never breaks the rest of the search."""
    title = str(channel.get("title", "")).strip()
    if not title:
        return None
    playlist = _best_playlist(channel.get("playlists"))
    if playlist is None:
        return None
    pls_url = str(playlist.get("url", "")).strip()
    if not pls_url:
        return None
    try:
        refuse_in_safe_mode(safe_mode)
        stream_url = first_stream_url_from_pls(_http_text(pls_url))
    except SomaFmError:
        return None
    if not stream_url:
        return None
    genre_tags = tuple(
        part.strip() for part in str(channel.get("genre", "")).split("|") if part.strip()
    )
    fmt = str(playlist.get("format", "")).upper()
    return RadioStation(
        name=title,
        stream_url=stream_url,
        station_uuid="",  # never a RadioBrowser id -- see the module docstring
        homepage="https://somafm.com/",
        favicon=str(channel.get("image", "")),
        country="United States",
        language="English",
        tags=(*genre_tags, _CATEGORY_TAG),
        codec=fmt,
    )


def search_stations(query: str = "", *, safe_mode: bool = False) -> list[RadioStation]:
    """Channels matching *query* against title/description/genre (or every
    channel, if *query* is blank), each resolved to a real playable stream.

    Matching runs client-side over the one small (~30-entry) channel list;
    only *matching* channels pay the extra playlist-resolution round trip,
    done concurrently since they're independent, tiny text fetches.
    """
    refuse_in_safe_mode(safe_mode)
    channels = [
        c for c in channels_from_json(_http_json(_CHANNELS_URL)) if _channel_matches(c, query)
    ]
    if not channels:
        return []
    with ThreadPoolExecutor(max_workers=min(_MAX_RESOLVE_WORKERS, len(channels))) as pool:
        resolved = list(pool.map(lambda c: _resolve_channel(c, safe_mode=safe_mode), channels))
    return [station for station in resolved if station is not None]
