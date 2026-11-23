"""Locus Sonus Soundmap: open microphones streaming live from around the world.

Locus Sonus, a sound-art research lab, runs a map of "open microphones": a
microphone left running on a balcony in Amsterdam, a hydrophone in a canal, a
forest in New York state, each streaming live, all the time. Its soundmap
publishes the ones on air right now as one small JSON list,
``locusonus.org/soundmap/list/active/json/name``: for each, a name, a stream
address, the city and country, and the person who set it up.

So Browse Stations > Locus Sonus Soundmap lists every open microphone on air,
A to Z, each a station that plays, records and saves like any other, named as
the soundmap names it, with its country after it once ("amsterdam, hydrophile
1 (Netherlands)"). Find Streams from a Website reads the same list when it is
given the soundmap's own page.

The idea of offering the soundmap's active list is from Andre Louis's
StreamSift (https://github.com/OnjLouis/StreamSift); this is QUILL's own code.

One HTTPS GET to a single reviewed egress site (:func:`_fetch` -- see
``quill/tools/network_egress_entries_radio_listening.py``), verified TLS, a
bounded timeout and a 1 MB cap, reached only by opening or refreshing the
branch or scanning the soundmap page, and refused in Safe Mode via
:func:`refuse_in_safe_mode`. Cached for half an hour, because which
microphones are on air changes through the day. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from quill.core import http_client
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation

__all__ = [
    "EMPTY_NOTE",
    "LIST_URL",
    "SOURCE",
    "LocusSonusError",
    "fetch_stations",
    "is_soundmap_page",
    "parse_active_list",
    "refuse_in_safe_mode",
]

SOURCE = "Locus Sonus"
LIST_URL = "https://locusonus.org/soundmap/list/active/json/name"
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 1_000_000
_CACHE_KEY = "locussonus:active"
_CACHE_MAX_AGE_SECONDS = 30 * 60
_MAX_STATIONS = 500
_HOSTS = ("locusonus.org", "www.locusonus.org")
#: What the branch says when the soundmap answered with no microphones on air.
EMPTY_NOTE = "No open microphones are on air right now. Refresh to look again."


class LocusSonusError(CodedError):
    """A Locus Sonus Soundmap request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-LOCUSSONUS-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`LocusSonusError` when Safe Mode is active."""
    if safe_mode:
        raise LocusSonusError(
            "The Locus Sonus Soundmap is disabled in Safe Mode. "
            "Restart Quill Radio normally to browse it."
        )


def is_soundmap_page(url: str) -> bool:
    """True for the soundmap's own page, ``locusonus.org/soundmap/``."""
    parts = urllib.parse.urlsplit(url.strip())
    if (parts.hostname or "").lower() not in _HOSTS or parts.query:
        return False
    return parts.path.rstrip("/").lower() == "/soundmap"


def _text(value: object) -> str:
    return " ".join(str(value or "").split())[:100]


def _name(entry: dict[str, object]) -> str:
    """The soundmap's name for a microphone, cleaned: its dash read as a comma
    (an em dash between place and microphone becomes ", "), spaces single."""
    name = _text(entry.get("name")).replace("—", ",").replace("–", ",")
    name = " ".join(name.split()).replace(" ,", ",")
    return name.strip(" ,")


def _country(entry: dict[str, object], name: str) -> str:
    """The country, title-cased, or "" when the name already says it -- the
    row adds "(country)" itself, so it must not be said twice."""
    country = _text(entry.get("country"))
    if not country or country.casefold() in name.casefold():
        return ""
    return country.title()


def parse_active_list(payload: str) -> list[RadioStation]:
    """The active list as stations, A to Z (pure). Unreadable means none."""
    try:
        data = json.loads(payload)
    except (ValueError, TypeError):
        return []
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for entry in data if isinstance(data, list) else []:
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("url") or "").strip()
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("https", "http") or not parts.hostname or parts.query:
            continue
        name = _name(entry)
        if not name or url in seen:
            continue
        seen.add(url)
        artist = _text(entry.get("artist"))
        stations.append(
            RadioStation(
                name=name,
                stream_url=url,
                homepage=_text(entry.get("link")) or "https://locusonus.org/soundmap/",
                country=_country(entry, name),
                tags=tuple(t for t in ("Open microphone", artist) if t),
                codec=_text(entry.get("ext")).upper(),
                source=SOURCE,
            )
        )
        if len(stations) == _MAX_STATIONS:
            break
    return sorted(stations, key=lambda s: s.name.casefold())


def _fetch(url: str) -> str:
    """One HTTPS GET of the soundmap's active list -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise LocusSonusError("Only https:// URLs can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": http_client.user_agent()})
    try:
        with urllib.request.urlopen(
            request, timeout=_TIMEOUT_SECONDS, context=verified_ssl_context()
        ) as resp:
            payload: bytes = resp.read(_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise LocusSonusError(f"Could not reach the Locus Sonus Soundmap: {error}") from error
    if len(payload) > _MAX_BYTES:
        raise LocusSonusError(
            "The Locus Sonus Soundmap sent a reply larger than 1 MB, so it was not read."
        )
    return payload.decode("utf-8", errors="replace")


def fetch_stations(*, safe_mode: bool = False, refresh: bool = False) -> list[RadioStation]:
    """Every open microphone on air, A to Z; the last good list if the fetch fails.

    Raises :class:`LocusSonusError` when there is neither an answer nor a
    cached list, so the branch can tell "could not be reached" from an
    answer that really has no microphones on air (see :data:`EMPTY_NOTE`).
    """
    refuse_in_safe_mode(safe_mode)
    payload, _age = directory_cache.resolve(
        _CACHE_KEY,
        lambda: _fetch(LIST_URL),
        max_age_seconds=_CACHE_MAX_AGE_SECONDS,
        refresh=refresh,
        empty="",
    )
    if not payload:
        error = LocusSonusError("The Locus Sonus Soundmap could not be reached.")
        # Read by browse_failure: unreachable, not "nothing on air".
        error.service_unreachable = True  # type: ignore[attr-defined]
        raise error
    return parse_active_list(str(payload))
