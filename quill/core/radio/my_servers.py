"""Point Quill Radio at a broadcaster's own server and browse what it is playing.

This is the branch no directory can give you. TuneIn never listed the community
station three towns over; Radio Browser never indexed the church, the school, or
the reading service that runs its own box. But almost all of them run **Icecast**
or **SHOUTcast**, and both publish, with no key and no registration, a complete
list of what they are currently serving:

* Icecast 2 -- ``/status-json.xsl``: every mount, with its name, description,
  genre, bitrate, listener count, **and what is playing on it right now**.
* SHOUTcast v2 -- ``/stat`` (XML), and v1 -- ``/7.html`` (a single comma-separated
  line). Less detail, same idea.

So the listener supplies an address once and browses it forever after, with
now-playing text on every mount, and Refresh brings it up to date.

The stored list is deliberately its own thing rather than a kind of favorite: a
favorite is *a station*, and this is *a place that has stations* -- the mounts
behind it change, which is the entire point.

Every request funnels through the single reviewed egress site (:func:`_fetch` --
see ``quill/tools/network_egress_audit.py``), reached only by adding or opening a
server, and disabled in Safe Mode via :func:`refuse_in_safe_mode`.

**This one honestly cannot be HTTPS-only.** A large share of small Icecast boxes
are plain http on a high port and always have been; refusing them would refuse
the entire audience this branch exists for. So http is accepted here, the address
is one the listener typed themselves, nothing is sent but a GET, and no
credential is ever attached. That is a deliberate, narrow exception and it is
written down rather than quietly made.

wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.paths import app_data_dir
from quill.core.radio.models import RadioStation
from quill.core.storage import read_json, write_json_atomic

_USER_AGENT = f"QUILL-Radio/{__version__} (+https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 12.0
_MAX_BYTES = 2_000_000
_FILE_NAME = "radio-my-servers.json"

#: Probed in order. Icecast first because it is both the most common and the
#: most informative; the SHOUTcast endpoints are cheap fallbacks.
_STATUS_PATHS = ("/status-json.xsl", "/stat", "/7.html")


class MyServersError(CodedError):
    """A listener-added server could not be read (network, or Safe Mode)."""

    code = "QUILL-RADIO-MYSERVERS-REQUEST"


@dataclass(frozen=True, slots=True)
class Server:
    """One server the listener added."""

    root: str
    name: str = ""

    @property
    def display_name(self) -> str:
        return self.name or urllib.parse.urlsplit(self.root).netloc or self.root


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`MyServersError` when Safe Mode is active."""
    if safe_mode:
        raise MyServersError(
            "Your own servers are disabled in Safe Mode. Restart QUILL normally to browse them."
        )


def normalize_root(url: str) -> str:
    """A server root from whatever the listener pasted (pure).

    They will paste a stream URL as often as a server root -- that is what they
    have in hand -- so a path is dropped and the scheme defaulted. ``""`` for
    anything that is not an address at all.
    """
    value = (url or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"http://{value}"
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    host = parsed.netloc
    # "not a url" survives urlsplit once a scheme is prepended, so a netloc has
    # to actually look like a host: no whitespace, and either a dot, a port, or
    # the one bare name that is genuinely valid.
    if any(ch.isspace() for ch in host):
        return ""
    bare = host.rsplit("@", 1)[-1]
    if "." not in bare and ":" not in bare and bare.lower() != "localhost":
        return ""
    return f"{parsed.scheme}://{host}"


# --- the stored list ----------------------------------------------------------


class ServerStore:
    """The servers a listener has added, in the order they added them."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir

    def _path(self) -> Path:
        return (self._dir or app_data_dir()) / _FILE_NAME

    def all(self) -> list[Server]:
        try:
            data = read_json(self._path(), [])
        except OSError:
            return []
        servers: list[Server] = []
        for row in data if isinstance(data, list) else []:
            if not isinstance(row, dict):
                continue
            root = normalize_root(str(row.get("root", "")))
            if root:
                servers.append(Server(root=root, name=str(row.get("name", "")).strip()))
        return servers

    def add(self, url: str, name: str = "") -> Server | None:
        """Add a server. Returns the stored record, or ``None`` for a bad address.

        Adding one that is already there is a no-op rather than a duplicate --
        pasting the same station twice is a very ordinary thing to do.
        """
        root = normalize_root(url)
        if not root:
            return None
        servers = self.all()
        for existing in servers:
            if existing.root == root:
                return existing
        server = Server(root=root, name=name.strip())
        self._write([*servers, server])
        return server

    def remove(self, root: str) -> None:
        wanted = normalize_root(root)
        self._write([s for s in self.all() if s.root != wanted])

    def rename(self, root: str, name: str) -> None:
        wanted = normalize_root(root)
        self._write([
            Server(root=s.root, name=name.strip()) if s.root == wanted else s for s in self.all()
        ])

    def _write(self, servers: list[Server]) -> None:
        try:
            write_json_atomic(self._path(), [{"root": s.root, "name": s.name} for s in servers])
        except (OSError, TypeError, ValueError):  # pragma: no cover - environmental
            return


# --- reading a server ---------------------------------------------------------


def _fetch(url: str) -> str:
    """One GET of a listener-supplied server -- the reviewed egress site.

    See the module docstring for why http is accepted here and nowhere else.
    """
    if not url.startswith(("http://", "https://")):
        raise MyServersError("That does not look like a server address.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
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
        raise MyServersError(f"Could not reach that server: {error}") from error
    return payload.decode("utf-8", errors="replace")


def parse_icecast(json_text: str, root: str) -> list[RadioStation]:
    """Icecast's ``status-json.xsl`` into playable mounts (pure).

    A server with one mount reports ``source`` as an object rather than a list,
    which is the single most common way a naive parser returns nothing at all --
    and one-mount servers are exactly the small broadcasters this branch is for.

    Now-playing text rides along in the station's tags, so a mount can announce
    what it is playing before you tune to it.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    stats = data.get("icestats") if isinstance(data, dict) else None
    if not isinstance(stats, dict):
        return []
    sources = stats.get("source")
    if isinstance(sources, dict):
        sources = [sources]
    stations: list[RadioStation] = []
    for entry in sources if isinstance(sources, list) else []:
        if not isinstance(entry, dict):
            continue
        listen = str(entry.get("listenurl", "") or "").strip()
        if not listen:
            mount = str(entry.get("mount", "") or "").strip()
            listen = f"{root}{mount}" if mount.startswith("/") else ""
        if not listen:
            continue
        name = (
            str(entry.get("server_name", "") or "").strip()
            or str(entry.get("mount", "") or "").strip().lstrip("/")
            or listen
        )
        now_playing = str(entry.get("title", "") or "").strip()
        genre = str(entry.get("genre", "") or "").strip()
        bitrate = entry.get("bitrate") or entry.get("ice-bitrate") or 0
        stations.append(
            RadioStation(
                name=name,
                stream_url=listen,
                homepage=str(entry.get("server_url", "") or root),
                tags=tuple(t for t in (now_playing, genre) if t),
                codec=str(entry.get("server_type", "") or "").split("/")[-1].upper(),
                bitrate_kbps=int(bitrate) if str(bitrate).isdigit() else 0,
                source="My Servers",
            )
        )
    return stations


_SHOUTCAST_V2_RE = re.compile(
    r"<SERVERTITLE>(?P<title>[^<]*)</SERVERTITLE>.*?<SONGTITLE>(?P<song>[^<]*)</SONGTITLE>",
    re.IGNORECASE | re.DOTALL,
)


def parse_shoutcast(text: str, root: str) -> list[RadioStation]:
    """A SHOUTcast v2 ``/stat`` or v1 ``/7.html`` reply (pure).

    SHOUTcast serves one station per server, so this yields at most one row. v1's
    ``/7.html`` is a single comma-separated line whose last field is the current
    song -- crude, and it is what a great many old boxes still answer with.
    """
    match = _SHOUTCAST_V2_RE.search(text)
    if match:
        title = match.group("title").strip() or urllib.parse.urlsplit(root).netloc
        song = match.group("song").strip()
        return [
            RadioStation(
                name=title,
                stream_url=f"{root}/stream",
                homepage=root,
                tags=(song,) if song else (),
                source="My Servers",
            )
        ]
    stripped = re.sub(r"<[^>]+>", "", text).strip()
    if stripped.count(",") >= 6:
        song = stripped.rsplit(",", 1)[-1].strip()
        return [
            RadioStation(
                name=urllib.parse.urlsplit(root).netloc or root,
                stream_url=f"{root}/;stream.mp3",
                homepage=root,
                tags=(song,) if song else (),
                source="My Servers",
            )
        ]
    return []


def mounts(root: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Everything *root* is currently serving.

    Tries Icecast, then SHOUTcast v2, then v1, and returns the first that
    answers with something. A server that answers none of them yields an empty
    list rather than an error, so the branch says "nothing to browse there"
    instead of blaming the network.
    """
    refuse_in_safe_mode(safe_mode)
    base = normalize_root(root)
    if not base:
        return []
    for path in _STATUS_PATHS:
        try:
            body = _fetch(f"{base}{path}")
        except MyServersError:
            continue
        stations = (
            parse_icecast(body, base) if path.endswith(".xsl") else parse_shoutcast(body, base)
        )
        if stations:
            return stations
    return []


def probe(url: str, *, safe_mode: bool = False) -> tuple[str, int]:
    """Check an address before it is stored: ``(normalised root, mount count)``.

    So Add a Server can say "That server has 4 stations" or "Nothing there
    answered" *before* committing it to the list, rather than adding a branch
    that turns out to be empty.
    """
    base = normalize_root(url)
    if not base:
        return "", 0
    return base, len(mounts(base, safe_mode=safe_mode))
