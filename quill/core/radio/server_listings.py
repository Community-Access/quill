"""Read the list of every stream a streaming server is serving (pure).

An Icecast or SHOUTcast server says, with no key and no sign-in, what it is
serving right now. Find Streams from a Website reads that list when the address
it was given is the server itself, or a page that links to the server's status
page, and offers every stream on it instead of guessing one:

* **Icecast** ``/status-json.xsl`` -- every mount, with its name, bitrate,
  content type and listener count. :func:`parse_icecast_json`.
* **Icecast's HTML status page** -- ``/`` or ``/status.xsl`` -- for a server
  that has the JSON turned off. Each "Mount Point /name" card names the mount,
  its title, its content type and, on most servers, its listeners. Global's
  ``media-ssl.musicradio.com`` catalogue of every Global station is one of
  these. :func:`parse_icecast_html`.
* **SHOUTcast v2** ``/statistics?json=1`` -- every stream the server carries
  (one server can carry several), with its path, title, bitrate, content type
  and current listeners. :func:`parse_shoutcast_json`.

Only audio is kept (``audio/*`` or ``application/ogg``, never a playlist type);
a SHOUTcast stream whose source is down (``streamstatus`` 0) is left out; and a
mount is always built on the server that answered, never on a host or port the
statistics name, so a backend address behind a proxy is never contacted. Every
mount is then checked like any other candidate by
:mod:`quill.core.radio.live_check`.

The idea of listing every stream a server reports, with its listeners, is from
Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift); this is
QUILL's own implementation, not a port.

No network: the caller (``link_finder``) fetches. wx-free, strict-typed.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
from dataclasses import dataclass

__all__ = [
    "MAX_MOUNTS",
    "ServerMount",
    "is_audio_type",
    "is_front_page",
    "parse_icecast_html",
    "parse_icecast_json",
    "parse_shoutcast_json",
    "server_kind",
    "server_root",
    "status_kind",
]

#: The most mounts one server listing contributes.
MAX_MOUNTS = 400

ICECAST = "icecast"
SHOUTCAST = "shoutcast"

#: Paths whose answer says what a server is serving.
ICECAST_JSON = "/status-json.xsl"
SHOUTCAST_JSON = "/statistics?json=1"

_ROOT_PATHS = ("", "/", "/index.html", "/status.xsl")
_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]+")
_MOUNT_HEADING_RE = re.compile(r"Mount\s+Point\s+(/[^\s<:]*)", re.IGNORECASE)
_CELL_PAIR_RE = re.compile(r"<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True, slots=True)
class ServerMount:
    """One stream a server lists: where it is, and what the server says of it."""

    url: str
    name: str = ""
    bitrate_kbps: int = 0
    #: How many are listening now, or ``None`` when the server did not say.
    listeners: int | None = None


def is_audio_type(mime: str) -> bool:
    """True for an audio content type that is a stream, not a playlist."""
    lowered = mime.strip().lower()
    if lowered == "application/ogg":
        return True
    if not lowered.startswith("audio/"):
        return False
    return not any(word in lowered for word in ("mpegurl", "scpls", "xspf"))


def server_root(url: str) -> str:
    """``scheme://host[:port]`` of *url*, or "" when it has no host."""
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.netloc else ""


def status_kind(url: str) -> str:
    """:data:`ICECAST` or :data:`SHOUTCAST` when *url* is that server's status
    page or statistics, else "". Pure: by address alone."""
    parts = urllib.parse.urlsplit(url)
    path = parts.path.lower()
    if path.endswith(("/status.xsl", "/status-json.xsl")):
        return ICECAST
    query = urllib.parse.parse_qs(parts.query)
    if path == "/statistics" or (path == "/index.html" and "sid" in query):
        return SHOUTCAST
    return ""


def is_front_page(url: str) -> bool:
    """True when *url* is a server's front page: ``/``, ``/index.html`` or
    ``/status.xsl`` -- where an Icecast server shows its mounts."""
    return urllib.parse.urlsplit(url).path.lower() in _ROOT_PATHS


def server_kind(url: str, title: str) -> str:
    """Which server answered at the root of *url*, judged by its page title.

    Only a server's own front page counts -- ``/``, ``/index.html`` or
    ``/status.xsl`` -- so a station site that merely mentions Icecast is not
    taken for a server.
    """
    if not is_front_page(url):
        return ""
    lowered = title.lower()
    if "icecast" in lowered:
        return ICECAST
    if "shoutcast" in lowered:
        return SHOUTCAST
    return ""


def _mount_url(root: str, path: str) -> str:
    """*path* on *root*, or "" when it is not a plain mount path.

    A status or admin route is never turned into a stream, and neither is a
    path that would leave the server (``//host``) or climb out of it.
    """
    path = path.strip()
    if not path.startswith("/") or path.startswith("//") or len(path) > 512:
        return ""
    if "?" in path or "#" in path or "\\" in path:
        return ""
    decoded = urllib.parse.unquote(path)
    segments = [s.lower() for s in decoded.split("/")]
    if any(s in (".", "..", "admin") for s in segments):
        return ""
    if decoded.lower() in (ICECAST_JSON, "/status.xsl", "/statistics", "/stats"):
        return ""
    return root + path


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _kbps(value: object) -> int:
    rate = _int(value)
    return rate if rate is not None and 0 < rate <= 10_000 else 0


def _listeners(value: object) -> int | None:
    count = _int(value)
    return count if count is not None and count >= 0 else None


def _clean(value: object) -> str:
    """Server-supplied text made safe to show and speak: no control
    characters, whitespace collapsed, at most 60 characters."""
    text = " ".join(_CONTROL_RE.sub(" ", str(value or "")).split())
    return text if len(text) <= 60 else text[:60].rsplit(" ", 1)[0]


class _Listing:
    """Mounts in order, each once, at most :data:`MAX_MOUNTS`."""

    def __init__(self) -> None:
        self.mounts: list[ServerMount] = []
        self._seen: set[str] = set()

    def add(self, mount: ServerMount) -> None:
        if mount.url and mount.url not in self._seen and len(self.mounts) < MAX_MOUNTS:
            self._seen.add(mount.url)
            self.mounts.append(mount)


def _json(text: str) -> object:
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def parse_icecast_json(text: str, root: str) -> list[ServerMount]:
    """Icecast's ``status-json.xsl``: every audio mount, built on *root*.

    A one-mount server reports ``source`` as an object, not a list. The mount
    is the path of ``listenurl`` (or ``mount``) on the server that answered.
    """
    data = _json(text)
    stats = data.get("icestats") if isinstance(data, dict) else None
    sources = stats.get("source") if isinstance(stats, dict) else None
    if isinstance(sources, dict):
        sources = [sources]
    listing = _Listing()
    for entry in sources if isinstance(sources, list) else []:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("server_type") or "")
        if kind and not is_audio_type(kind):
            continue
        listen = str(entry.get("listenurl") or "")
        path = urllib.parse.urlsplit(listen).path if listen else str(entry.get("mount") or "")
        listing.add(
            ServerMount(
                url=_mount_url(root, path),
                name=_clean(entry.get("server_name")),
                bitrate_kbps=_kbps(entry.get("bitrate") or entry.get("ice-bitrate")),
                listeners=_listeners(entry.get("listeners")),
            )
        )
    return listing.mounts


def parse_shoutcast_json(text: str, root: str) -> list[ServerMount]:
    """SHOUTcast v2's ``/statistics?json=1``: every stream that is on air."""
    data = _json(text)
    streams = data.get("streams") if isinstance(data, dict) else None
    listing = _Listing()
    for entry in streams if isinstance(streams, list) else []:
        if not isinstance(entry, dict) or _int(entry.get("streamstatus")) != 1:
            continue
        if not is_audio_type(str(entry.get("content") or "")):
            continue
        path = str(entry.get("streampath") or "")
        url = root + "/" if path == "/" else _mount_url(root, path)
        listing.add(
            ServerMount(
                url=url,
                name=_clean(entry.get("servertitle")),
                bitrate_kbps=_kbps(entry.get("bitrate")),
                listeners=_listeners(entry.get("currentlisteners")),
            )
        )
    return listing.mounts


def _cell_text(fragment: str) -> str:
    return _clean(html.unescape(_TAG_RE.sub(" ", fragment)))


def parse_icecast_html(page: str, url: str) -> list[ServerMount]:
    """An Icecast HTML status page: each "Mount Point" card with an audio type.

    Reads the current card layout and the older ones alike, because each puts
    the heading first and a two-column table of facts after it. A card that
    states no content type is skipped, so only what the server calls audio is
    offered; the page's ``.m3u`` links remain the caller's fallback.
    """
    root = server_root(url)
    headings = list(_MOUNT_HEADING_RE.finditer(page))
    listing = _Listing()
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(page)
        facts: dict[str, str] = {}
        for label, value in _CELL_PAIR_RE.findall(page[heading.end() : end]):
            facts.setdefault(_cell_text(label).rstrip(":").lower(), _cell_text(value))
        if not is_audio_type(facts.get("content type", "")):
            continue
        listeners = facts.get("current listeners") or facts.get("listeners (current)") or ""
        listing.add(
            ServerMount(
                url=_mount_url(root, heading.group(1)),
                name=facts.get("stream title") or facts.get("stream name") or "",
                bitrate_kbps=_kbps(facts.get("bitrate", "")),
                listeners=_listeners(listeners),
            )
        )
    return listing.mounts
