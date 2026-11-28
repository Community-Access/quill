"""Radio Garden: find an individual public station, and play it where it can be.

Radio Garden (https://radio.garden) has **no official public API**. This module
uses only the three endpoints that its own web page calls and that open-source
clients have long relied on, and nothing else:

* ``/api/search?q=<words>`` -- stations, places and countries matching the words;
  only the stations ("channels") are used;
* ``/api/ara/content/channel/<id>`` -- one station's title and place; and
* ``/api/ara/content/listen/<id>/channel.mp3`` -- answers with a redirect to the
  station's real stream. The redirect is followed (by hand, five hops at most,
  each hop re-checked as a public address, by :mod:`quill.core.net_public`) and
  the **real stream address** it ends at is what is checked and listed. The
  Radio Garden address itself is never what plays.

Because the service is not documented, it is treated as something that can stop
working or refuse a program at any time (it sits behind a bot filter that answers
some clients with a web page). Every failure is therefore a plain sentence and
never an error: "Radio Garden did not answer the way it usually does." The live
check is the same one every other stream gets; a station whose address does not
turn out to be audio is not listed.

Rules, as for the rest of Find Streams: public HTTPS only; answers capped at
512 KB and parsed as untrusted data; Safe Mode contacts nothing; a request is
made only for something the listener typed or pasted, never in the background;
and at most :data:`MAX_PLAYBACK_LOOKUPS` stations are looked up for one search.

The idea of reading more places comes from Andre Louis's StreamSift
(https://github.com/OnjLouis/StreamSift, MIT); Radio Garden's use here is
QUILL's own. wx-free, strict-typed; the network is passed in.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.radio import live_check
from quill.core.radio.live_check import HttpReply
from quill.core.radio.page_links import PageStreamCandidate

__all__ = [
    "HOST",
    "MAX_PLAYBACK_LOOKUPS",
    "SOURCE",
    "Hit",
    "channel_title",
    "listen_url",
    "parse_search",
    "resolve",
    "search",
    "station_id",
]

HOST = "radio.garden"
SOURCE = "Radio Garden"
MAX_PLAYBACK_LOOKUPS = 5
_MAX_BYTES = 512 * 1024
_TIMEOUT = 12.0
_ID = re.compile(r"^[A-Za-z0-9_-]{4,32}$")
_STATION_PATH = re.compile(r"/listen/[^/]+/([A-Za-z0-9_-]{4,32})/?$")

#: ``get(url, timeout, max_bytes) -> HttpReply``; raises on a network failure.
Fetch = Callable[[str, float, int], HttpReply]

NOT_ANSWERING = "Radio Garden did not answer the way it usually does, so nothing was found there."
NO_PLAYBACK = "Radio Garden does not offer a stream for that station right now."


@dataclass(frozen=True, slots=True)
class Hit:
    """One station a search found."""

    id: str
    title: str
    place: str = ""


def station_id(text: str) -> str:
    """The station id in a pasted Radio Garden station page, or ``""`` (pure).

    ``https://radio.garden/listen/kexp-90-3/Zk1UxX-Y`` -> ``"Zk1UxX-Y"``. The
    page of a place, a country or the map is not a station and gives ``""``.
    """
    value = text.strip()
    if not value or any(ch.isspace() for ch in value):
        return ""
    parts = urllib.parse.urlsplit(value if "://" in value else f"https://{value}")
    host = (parts.hostname or "").lower().removeprefix("www.")
    if host != HOST:
        return ""
    found = _STATION_PATH.search(parts.path)
    return found.group(1) if found else ""


def listen_url(channel_id: str) -> str:
    return f"https://{HOST}/api/ara/content/listen/{urllib.parse.quote(channel_id)}/channel.mp3"


def _search_url(query: str) -> str:
    return f"https://{HOST}/api/search?q={urllib.parse.quote(query)}"


def _channel_url(channel_id: str) -> str:
    return f"https://{HOST}/api/ara/content/channel/{urllib.parse.quote(channel_id)}"


def _json(reply: HttpReply) -> Any:
    """The reply's JSON, or ``None`` when it is anything else (a challenge page)."""
    if reply.status >= 400:
        return None
    try:
        return json.loads(reply.body.decode("utf-8", errors="replace"))
    except ValueError:
        return None


def parse_search(payload: Any) -> list[Hit]:
    """Stations out of a search answer; anything unexpected gives fewer rows."""
    hits: list[Hit] = []
    seen: set[str] = set()
    try:
        rows = payload["hits"]["hits"]
    except (KeyError, TypeError):
        return hits
    if not isinstance(rows, list):
        return hits
    for row in rows:
        source = row.get("_source") if isinstance(row, dict) else None
        if not isinstance(source, dict) or source.get("type") != "channel":
            continue
        url = source.get("url")
        title = source.get("title")
        found = _STATION_PATH.search(url) if isinstance(url, str) else None
        if not found or not isinstance(title, str) or not title.strip():
            continue
        channel = found.group(1)
        if channel in seen or not _ID.match(channel):
            continue
        seen.add(channel)
        place = source.get("subtitle")
        hits.append(Hit(channel, " ".join(title.split()), place if isinstance(place, str) else ""))
    return hits


def search(query: str, fetch: Fetch) -> list[Hit] | None:
    """Stations matching *query*; ``None`` when Radio Garden did not answer usefully."""
    words = " ".join(query.split())
    if not words:
        return []
    try:
        payload = _json(fetch(_search_url(words), _TIMEOUT, _MAX_BYTES))
    except Exception:  # noqa: BLE001 - an unreachable or refusing service is "no answer"
        return None
    return None if payload is None else parse_search(payload)


def channel_title(channel_id: str, fetch: Fetch) -> str:
    """A station's own name from its page's data, or ``""``."""
    try:
        payload = _json(fetch(_channel_url(channel_id), _TIMEOUT, _MAX_BYTES))
        title = payload["data"]["title"]
    except Exception:  # noqa: BLE001
        return ""
    return " ".join(title.split()) if isinstance(title, str) else ""


def resolve(hit: Hit, fetch: Fetch) -> PageStreamCandidate | None:
    """The playable stream behind one station, or ``None``.

    Asks for the station's listen address, lets the redirect run to the real
    stream, and judges what answered with the live check's own rules. A link
    that is a web page (a refusal) or gone is not offered.
    """
    start = listen_url(hit.id)
    try:
        reply = fetch(start, _TIMEOUT, live_check.PROBE_BYTES)
    except Exception:  # noqa: BLE001
        return None
    final = reply.final_url or start
    if urllib.parse.urlsplit(final).hostname == HOST:
        return None  # it never left Radio Garden, so there is no stream to play
    verdict, _follow = live_check.verdict_from_reply(reply, final)
    if verdict.state == live_check.NOT_AUDIO:
        return None
    return PageStreamCandidate(
        url=final,
        reason=f"found in the {SOURCE} directory",
        label=hit.title,
        check=verdict.state,
        codec=verdict.codec,
        bitrate_kbps=verdict.bitrate_kbps,
        stream_name=verdict.name or "",
        genre=verdict.genre,
        check_note=verdict.note,
        label_is_name=True,
    )
