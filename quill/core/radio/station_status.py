"""Server "now playing" status endpoints -- the free fallback for #1111.

When a stream sends no ICY ``StreamTitle`` (see :mod:`quill.core.radio.icy`)
and the player exposes no in-band title (mpv ``media-title``), the station's
own Icecast/SHOUTcast server usually still publishes the current track over a
small status endpoint:

* Icecast: ``/status-json.xsl`` -- JSON, ``icestats.source[].title`` (or
  ``yp_currently_playing``), one entry per mount.
* SHOUTcast v2: ``/stats?json=1`` -- JSON, ``{"songtitle": "..."}``.
* SHOUTcast v1: ``/7.html`` -- a comma-separated line whose 7th field onward is
  the song title.

:func:`read_server_now_playing` derives these endpoints from the stream URL's
own host/port (never a third party -- the same host the user is already
streaming), tries them in order, and returns the current ``Artist - Title``
string or ``""``. This is the free tier of the "what's playing?" resolver; the
opt-in acoustic-fingerprinting tier (#1111 tier 3) is separate.

GATE-9 / network-egress: the outbound calls contact only the stream URL's own
host, run off-thread on the same playback-driven cadence / explicit What's
Playing command as the ICY tap, are refused in Safe Mode (``safe_mode``), and
read a single small response. A missing title always degrades to ``""``, never
an error. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request

_TIMEOUT_SECONDS = 8.0
_MAX_BYTES = 256 * 1024
_USER_AGENT = "QUILL Radio"

#: Strip HTML tags from a SHOUTcast v1 ``/7.html`` body before splitting fields.
_TAG_RE = re.compile(r"<[^>]+>")


def status_endpoint_candidates(stream_url: str) -> list[tuple[str, str, str]]:
    """``(endpoint_url, kind, mount)`` triples to try, or ``[]`` for non-http.

    All endpoints are on the stream's own host/port. ``kind`` selects the
    parser; ``mount`` (the stream path) lets the Icecast parser pick the right
    source when a server hosts several mounts.
    """
    parsed = urllib.parse.urlsplit(stream_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return []
    base = f"{parsed.scheme}://{parsed.netloc}"
    mount = parsed.path or ""
    return [
        (f"{base}/status-json.xsl", "icecast", mount),
        (f"{base}/stats?json=1", "shoutcast_v2", mount),
        (f"{base}/7.html", "shoutcast_v1", mount),
    ]


def parse_icecast_status(json_text: str, *, mount: str = "") -> str:
    """Current title from an Icecast ``/status-json.xsl`` body ("" if none).

    Prefers the source whose ``listenurl`` matches *mount* (multi-mount
    servers), else the first source that carries a title. Never raises.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return ""
    stats = data.get("icestats") if isinstance(data, dict) else None
    if not isinstance(stats, dict):
        return ""
    sources = stats.get("source")
    if isinstance(sources, dict):
        sources = [sources]
    if not isinstance(sources, list):
        return ""

    def title_of(src: object) -> str:
        if not isinstance(src, dict):
            return ""
        return str(src.get("title") or src.get("yp_currently_playing") or "").strip()

    if mount:
        for src in sources:
            if isinstance(src, dict) and str(src.get("listenurl") or "").endswith(mount):
                title = title_of(src)
                if title:
                    return title
    for src in sources:
        title = title_of(src)
        if title:
            return title
    return ""


def parse_shoutcast_v2_status(json_text: str) -> str:
    """Current title from a SHOUTcast v2 ``/stats?json=1`` body ("" if none)."""
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("songtitle") or "").strip()


def parse_shoutcast_v1_status(text: str) -> str:
    """Current title from a SHOUTcast v1 ``/7.html`` body ("" if none).

    The body is ``<current>,<status>,<peak>,<max>,<unique>,<bitrate>,<song>``;
    the song title is the 7th field onward (re-joined, so a title with its own
    commas survives)."""
    stripped = _TAG_RE.sub("", text).strip()
    for line in stripped.splitlines():
        fields = line.split(",")
        if len(fields) >= 7:
            return ",".join(fields[6:]).strip()
    return ""


def _http_get_text(url: str, timeout: float) -> str:
    """One GET returning decoded text, verified TLS; "" on any failure."""
    if not url.lower().startswith(("http://", "https://")):
        return ""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(  # noqa: S310 - http(s) checked above
            request, timeout=timeout, context=context
        ) as response:
            payload: bytes = response.read(_MAX_BYTES)
    except Exception:  # noqa: BLE001 - a missing title must never surface
        return ""
    return payload.decode("utf-8", errors="replace")


def read_server_now_playing(
    stream_url: str, *, timeout: float = _TIMEOUT_SECONDS, safe_mode: bool = False
) -> str:
    """The current track from the stream server's status endpoint, or "".

    Tries the Icecast and SHOUTcast status endpoints on the stream's own host in
    order and returns the first non-empty title. Refused in Safe Mode. Any
    network or parse hiccup reads as "no title" so it never disturbs playback.
    """
    if safe_mode:
        return ""
    for url, kind, mount in status_endpoint_candidates(stream_url):
        text = _http_get_text(url, timeout)
        if not text:
            continue
        if kind == "icecast":
            title = parse_icecast_status(text, mount=mount)
        elif kind == "shoutcast_v2":
            title = parse_shoutcast_v2_status(text)
        else:
            title = parse_shoutcast_v1_status(text)
        if title:
            return title
    return ""
