"""Television: the iptv.org community catalog, browsable and searchable.

WHAT THIS IS
------------
`iptv.org <https://iptv.org>`_ maintains the largest open, community-collected
index of publicly available television streams -- and publishes it as plain
JSON files on GitHub Pages, keyless, exactly the way Radio Browser publishes
radio. Quill Radio already plays HLS video with captions and audio-track
selection, so television is a *catalog* problem here, not a playback one: join
the published files, cache the result, and the tree gains ~10,000 TV channels
by country and by category.

Six files, all from ``iptv-org.github.io`` (measured 2026-08-27):

* ``channels.json`` -- 40,815 channels: id, name, country, categories, flags.
* ``streams.json`` -- 16,941 stream URLs, keyed to channel ids and feeds.
* ``feeds.json`` -- broadcast areas per feed: ``c/US`` (national), ``s/US-MO``
  (a state or other subdivision), ``ct/USNYC`` (a city).
* ``subdivisions.json`` / ``cities.json`` -- names for those codes, and each
  city's own subdivision, which is how a city channel finds its state.
* ``countries.json`` -- names for the country codes.

The broadcast areas are what turn a 1,700-channel country into a browsable
place: a country with local channels opens into **Nationwide**, then its
states, each state carrying its own and its cities' channels. A five-digit US
ZIP code in a TV search is mapped to its state through a bundled prefix table
(approximate at the edges, exact enough to narrow a channel list) -- the
closest an open catalog gets to "what is on around me", and honestly labelled
as that rather than as reception prediction, which is AntennaWeb's job and the
reason that row opens a browser.

WHAT IS DELIBERATELY DROPPED, and why each is a decision
--------------------------------------------------------
* **Channels flagged NSFW** (375). This is a family of applications; the flag
  exists in the data precisely so a client can make this choice, and this one
  does.
* **Closed channels** (1,341) and channels with no stream at all -- a row that
  cannot play is worse than no row.
* **Streams that require a spoofed Referer or User-Agent** (~1,000 of 14,991).
  The player sends honest headers, the same policy as every directory here;
  a stream that only answers a disguise would simply fail on Enter, and a row
  that fails on Enter is the fault this catalog is being filtered to avoid.
* Plain ``http://`` streams are **kept**, per the Team-FM ruling recorded in
  ``magic.md``: an individual stream risks only itself, and dropping http would
  silently exclude exactly the small broadcasters this catalog is richest in.

After all four cuts: ~9,900 playable channels.

THE GUIDE
---------
iptv.org's channel ids are XMLTV ids (``BBCOne.uk``), so a listener who drops
an XMLTV programme guide at ``<data dir>/tv_guide.xml`` gets "Now / Next" on
every channel the guide covers -- see :mod:`quill.core.radio.xmltv` and
:func:`fetch_channels`. No guide is fetched from anywhere: XMLTV feeds are a
choose-your-own ecosystem (the ``iptv-org/epg`` project generates them), and a
file the listener placed is consent in its plainest form.

One HTTPS GET per file to a single reviewed egress site (:func:`_fetch` -- see
``quill/tools/network_egress_audit.py``), cached for a day as compact rows, so
a day's browsing and searching is at most four requests -- and usually zero,
because the browse warm-up fills this cache in the background. Refused in Safe
Mode via :func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache
from quill.core.radio.models import RadioStation
from quill.core.radio.natural_order import natural_key

_BASE = "https://iptv-org.github.io/api/"
_TIMEOUT_SECONDS = 45.0
#: channels.json measured 10.3 MB and streams.json 3.5 MB on 2026-08-27; the
#: caps leave room to grow without leaving room for a redirect to something
#: that is not the catalog at all.
_MAX_CHANNELS_BYTES = 40_000_000
_MAX_STREAMS_BYTES = 16_000_000
_MAX_SMALL_BYTES = 1_000_000
#: feeds.json measured 7.9 MB and cities.json 5.6 MB on 2026-08-27.
_MAX_FEEDS_BYTES = 24_000_000
_MAX_CITIES_BYTES = 16_000_000
_USER_AGENT: str | None = None

CATEGORY_LABEL = "TV"
#: Spoken/shown attribution. It names the filtering because "9,900 channels"
#: invites the question of where they came from and what was left out.
CATALOG_CREDIT = "the iptv.org community catalog, playable channels only"

_CACHE_KEY = "iptv:channels"
#: Seven days, not the one day the other cached directories use (asked for
#: 2026-08-27): this catalog is the heaviest refresh in the app -- ~28 MB
#: across the files -- it turns over slowly, and a stale channel list is a
#: working branch. The TV root carries an explicit "Update the channel list
#: now" action for whoever wants today's copy today.
_CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60

#: Stream-quality preference, best first. Rows carry the chosen quality so the
#: details panel can say it; a listener on a slow link reads it before playing.
_QUALITY_ORDER = ("2160p", "1080p", "720p", "576p", "480p", "360p", "240p")


class IptvError(CodedError):
    """A TV catalog request failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-IPTV-REQUEST"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`IptvError` when Safe Mode is active."""
    if safe_mode:
        raise IptvError(
            "The TV catalog is disabled in Safe Mode. Restart QUILL normally to browse it."
        )


# --- pure joining ------------------------------------------------------------


def _quality_rank(quality: object) -> int:
    value = str(quality or "").strip().lower()
    try:
        return _QUALITY_ORDER.index(value)
    except ValueError:
        return len(_QUALITY_ORDER)


def join_channels(
    channels_json: str,
    streams_json: str,
    countries_json: str,
    *,
    feeds_json: str = "",
    subdivisions_json: str = "",
    cities_json: str = "",
) -> list[dict[str, Any]]:
    """The playable TV catalog as compact rows (pure).

    One row per channel that survives the four cuts the module docstring
    records, carrying only what a browse row needs: this is what gets cached,
    so it is kept to a tenth of the raw payload.
    """
    try:
        channels = json.loads(channels_json)
        streams = json.loads(streams_json)
        countries = json.loads(countries_json)
    except (TypeError, ValueError):
        return []
    if not isinstance(channels, list) or not isinstance(streams, list):
        return []
    country_names: dict[str, str] = {}
    if isinstance(countries, list):
        for entry in countries:
            if isinstance(entry, dict) and entry.get("code"):
                country_names[str(entry["code"])] = str(entry.get("name") or entry["code"])

    # Broadcast areas, from each channel's main feed: national / state / city.
    # A city rolls up to its state through cities.json, so "By State" carries a
    # state's own channels and its cities' channels together.
    city_names: dict[str, str] = {}
    city_state: dict[str, str] = {}
    sub_names: dict[str, str] = {}
    try:
        for entry in json.loads(subdivisions_json or "[]") or []:
            if isinstance(entry, dict) and entry.get("code"):
                sub_names[str(entry["code"])] = str(entry.get("name") or entry["code"])
        for entry in json.loads(cities_json or "[]") or []:
            if isinstance(entry, dict) and entry.get("code"):
                city_names[str(entry["code"])] = str(entry.get("name") or entry["code"])
                if entry.get("subdivision"):
                    city_state[str(entry["code"])] = str(entry["subdivision"])
    except (TypeError, ValueError):
        pass
    areas: dict[str, list[str]] = {}
    try:
        for entry in json.loads(feeds_json or "[]") or []:
            if isinstance(entry, dict) and entry.get("channel") and entry.get("is_main"):
                held = entry.get("broadcast_area")
                if isinstance(held, list):
                    areas[str(entry["channel"])] = [str(a) for a in held]
    except (TypeError, ValueError):
        pass

    def _area_of(channel_id: str) -> tuple[str, str, str]:
        """``(kind, state code, city name)`` for a channel: the finest area its
        main feed declares. ``("", "", "")`` when the feed says nothing."""
        best_kind, state, city = "", "", ""
        for area in areas.get(channel_id, []):
            kind, _slash, code = area.partition("/")
            if kind == "ct" and code in city_state:
                return ("city", city_state[code], city_names.get(code, code))
            if kind == "s" and best_kind != "city":
                best_kind, state = "state", code
            elif kind == "c" and not best_kind:
                best_kind = "national"
        return (best_kind, state, city)

    # The best honest stream per channel: no disguise headers, best quality.
    best: dict[str, dict[str, Any]] = {}
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        channel_id = stream.get("channel")
        url = str(stream.get("url") or "").strip()
        if not channel_id or not url:
            continue
        if stream.get("referrer") or stream.get("user_agent"):
            continue
        held = best.get(channel_id)
        if held is None or _quality_rank(stream.get("quality")) < _quality_rank(
            held.get("quality")
        ):
            best[channel_id] = stream

    rows: list[dict[str, Any]] = []
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        channel_id = str(channel.get("id") or "")
        stream = best.get(channel_id)
        if stream is None or channel.get("is_nsfw") or channel.get("closed"):
            continue
        name = str(channel.get("name") or "").strip()
        if not name:
            continue
        code = str(channel.get("country") or "")
        area_kind, state_code, city = _area_of(channel_id)
        rows.append({
            "id": channel_id,
            "area": area_kind,
            "state": state_code,
            "state_name": sub_names.get(state_code, state_code.partition("-")[2] or ""),
            "city": city,
            "name": name,
            "url": str(stream.get("url") or ""),
            "country": country_names.get(code, code),
            "country_code": code,
            "categories": [str(c) for c in (channel.get("categories") or [])],
            "network": str(channel.get("network") or ""),
            "website": str(channel.get("website") or ""),
            "quality": str(stream.get("quality") or ""),
        })
    rows.sort(key=lambda row: natural_key(row["name"]))
    return rows


def to_station(row: dict[str, Any], *, now_next: str = "") -> RadioStation:
    """One compact row as a playable :class:`RadioStation` (pure)."""
    return RadioStation(
        name=str(row.get("name") or ""),
        stream_url=str(row.get("url") or ""),
        # Not Radio Browser's namespace -- see the same note in shoutcast.
        station_uuid="",
        homepage=str(row.get("website") or ""),
        country=str(row.get("country") or ""),
        tags=tuple(str(c).title() for c in (row.get("categories") or [])) or (CATEGORY_LABEL,),
        codec=str(row.get("quality") or ""),
        source=CATEGORY_LABEL,
        notes=now_next,
    )


# --- network -----------------------------------------------------------------


def _user_agent() -> str:
    global _USER_AGENT
    if _USER_AGENT is None:
        from quill import __version__

        _USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
    return _USER_AGENT


def _fetch(name: str, max_bytes: int) -> str:
    """One HTTPS GET of a published iptv.org catalog file -- the reviewed
    egress site. Reads one byte past the cap so a grown file is **detected**
    rather than parsed as a truncated document."""
    url = f"{_BASE}{name}"
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(max_bytes + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise IptvError(f"Could not reach the TV catalog: {error}") from error
    if len(payload) > max_bytes:
        raise IptvError(
            f"The TV catalog file {name} is larger than {max_bytes} bytes, so it was not "
            "read. Reading part of it would silently drop channels."
        )
    return payload.decode("utf-8", errors="replace")


def _fetch_joined() -> list[dict[str, Any]]:
    return join_channels(
        _fetch("channels.json", _MAX_CHANNELS_BYTES),
        _fetch("streams.json", _MAX_STREAMS_BYTES),
        _fetch("countries.json", _MAX_SMALL_BYTES),
        feeds_json=_fetch("feeds.json", _MAX_FEEDS_BYTES),
        subdivisions_json=_fetch("subdivisions.json", _MAX_SMALL_BYTES * 2),
        cities_json=_fetch("cities.json", _MAX_CITIES_BYTES),
    )


#: The parsed rows, held in process. The disk cache is megabytes of JSON, and
#: without this every branch expand -- each category, each state -- re-read
#: and re-parsed all of it ("opening iptv categories is also extremely slow",
#: 2026-08-27). One parse per run is the honest cost; the weekly disk cache is
#: still the source of truth, and an explicit refresh replaces both.
_rows_memo: list[dict[str, Any]] | None = None
_rows_lock = __import__("threading").Lock()


def fetch_rows(*, safe_mode: bool = False, refresh: bool = False) -> list[dict[str, Any]]:
    """The compact catalog rows: in-memory after the first read of a run."""
    global _rows_memo
    refuse_in_safe_mode(safe_mode)
    if not refresh:
        with _rows_lock:
            if _rows_memo is not None:
                return _rows_memo
    payload, _age = directory_cache.resolve(
        _CACHE_KEY,
        _fetch_joined,
        max_age_seconds=_CACHE_MAX_AGE_SECONDS,
        refresh=refresh,
        empty=[],
    )
    rows = [row for row in payload if isinstance(row, dict)] if isinstance(payload, list) else []
    with _rows_lock:
        # An empty answer is not memoised: a failed first fetch must not pin
        # "no channels" for the rest of the run.
        _rows_memo = rows or None
    return rows


def reset_for_tests() -> None:
    """Forget the in-process rows, so tests control what a fetch answers."""
    global _rows_memo
    with _rows_lock:
        _rows_memo = None


def _guide_note(channel_id: str) -> str:
    """ "Now / Next" for a channel, from the listener's own XMLTV file if any."""
    from quill.core.radio import xmltv

    return xmltv.now_next_note(channel_id)


def fetch_channels(*, safe_mode: bool = False, refresh: bool = False) -> list[RadioStation]:
    """Every playable channel, with guide notes where the listener has a guide."""
    return [
        to_station(row, now_next=_guide_note(str(row.get("id") or "")))
        for row in fetch_rows(safe_mode=safe_mode, refresh=refresh)
    ]


# --- the browse axes ---------------------------------------------------------


def countries(*, safe_mode: bool = False) -> list[tuple[str, str, int]]:
    """``(code, name, channel count)`` for every country with channels, A-Z."""
    counts: dict[str, tuple[str, int]] = {}
    for row in fetch_rows(safe_mode=safe_mode):
        code = str(row.get("country_code") or "")
        if not code:
            continue
        name = str(row.get("country") or code)
        held = counts.get(code)
        counts[code] = (name, (held[1] if held else 0) + 1)
    return sorted(
        ((code, name, count) for code, (name, count) in counts.items()),
        key=lambda entry: natural_key(entry[1]),
    )


def country_channels(code: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """One country's channels, guide notes included."""
    wanted = str(code or "").strip()
    return [
        to_station(row, now_next=_guide_note(str(row.get("id") or "")))
        for row in fetch_rows(safe_mode=safe_mode)
        if row.get("country_code") == wanted
    ]


def categories(*, safe_mode: bool = False) -> list[tuple[str, str, int]]:
    """``(id, label, channel count)`` for every category in use, A-Z."""
    counts: dict[str, int] = {}
    for row in fetch_rows(safe_mode=safe_mode):
        for category in row.get("categories") or []:
            key = str(category)
            counts[key] = counts.get(key, 0) + 1
    return sorted(
        ((key, key.title(), count) for key, count in counts.items()),
        key=lambda entry: natural_key(entry[1]),
    )


def category_channels(category: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """One category's channels, guide notes included."""
    wanted = str(category or "").strip().lower()
    return [
        to_station(row, now_next=_guide_note(str(row.get("id") or "")))
        for row in fetch_rows(safe_mode=safe_mode)
        if wanted in [str(c).lower() for c in (row.get("categories") or [])]
    ]


def search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """Channels matching *query* by name, network or country. In-memory over
    the cached catalog, so a warm search never touches the network. Never
    raises into a search fan-out."""
    wanted = str(query or "").strip().casefold()
    if not wanted:
        return []
    try:
        rows = fetch_rows(safe_mode=safe_mode)
    except IptvError:
        return []
    zip_state = state_for_zip(wanted)
    if zip_state:
        # A five-digit ZIP is a place, not a name: answer with that state's
        # channels (its cities' included), the way somebody typing 66044 means
        # "TV around Lawrence", not "channels with 66044 in the name".
        found = [row for row in rows if str(row.get("state") or "") == zip_state]
    else:
        found = [
            row
            for row in rows
            if wanted in str(row.get("name") or "").casefold()
            or wanted in str(row.get("network") or "").casefold()
            or wanted in str(row.get("city") or "").casefold()
            or wanted in str(row.get("state_name") or "").casefold()
            or wanted in str(row.get("country") or "").casefold()
        ]
    return [to_station(row, now_next=_guide_note(str(row.get("id") or ""))) for row in found[:200]]


#: US ZIP-code prefixes (first three digits) to state code, the well-known
#: postal table. Approximate at a handful of border prefixes, which is exactly
#: good enough for its one job: turning "66044" into "US-KS" so a TV search by
#: ZIP answers with that state's channels. It predicts nothing about reception
#: -- that is AntennaWeb's job, and the TV branch links there for it.
_ZIP_RANGES: tuple[tuple[int, int, str], ...] = (
    (5, 5, "NY"),
    (6, 9, "PR"),
    (10, 27, "MA"),
    (28, 29, "RI"),
    (30, 38, "NH"),
    (39, 49, "ME"),
    (50, 59, "VT"),
    (60, 69, "CT"),
    (70, 89, "NJ"),
    (100, 149, "NY"),
    (150, 196, "PA"),
    (197, 199, "DE"),
    (200, 205, "DC"),
    (206, 219, "MD"),
    (220, 246, "VA"),
    (247, 268, "WV"),
    (270, 289, "NC"),
    (290, 299, "SC"),
    (300, 319, "GA"),
    (320, 349, "FL"),
    (350, 369, "AL"),
    (370, 385, "TN"),
    (386, 397, "MS"),
    (398, 399, "GA"),
    (400, 427, "KY"),
    (430, 459, "OH"),
    (460, 479, "IN"),
    (480, 499, "MI"),
    (500, 528, "IA"),
    (530, 549, "WI"),
    (550, 567, "MN"),
    (570, 577, "SD"),
    (580, 588, "ND"),
    (590, 599, "MT"),
    (600, 629, "IL"),
    (630, 658, "MO"),
    (660, 679, "KS"),
    (680, 693, "NE"),
    (700, 714, "LA"),
    (716, 729, "AR"),
    (730, 749, "OK"),
    (750, 799, "TX"),
    (800, 816, "CO"),
    (820, 831, "WY"),
    (832, 838, "ID"),
    (840, 847, "UT"),
    (850, 865, "AZ"),
    (870, 884, "NM"),
    (885, 885, "TX"),
    (889, 898, "NV"),
    (900, 961, "CA"),
    (967, 968, "HI"),
    (970, 979, "OR"),
    (980, 994, "WA"),
    (995, 999, "AK"),
)


def state_for_zip(zip_code: str) -> str:
    """The ``US-XX`` subdivision for a five-digit ZIP (pure), or ``""``."""
    digits = str(zip_code or "").strip()
    if len(digits) != 5 or not digits.isdigit():
        return ""
    prefix = int(digits[:3])
    for low, high, state in _ZIP_RANGES:
        if low <= prefix <= high:
            return f"US-{state}"
    return ""


def country_areas(code: str, *, safe_mode: bool = False) -> list[tuple[str, str, int]]:
    """``("national"|state code, label, count)`` for one country, or ``[]``.

    Empty means the country's feeds declare no local areas, and the browse
    handler shows its channels flat -- which is most countries. Nationwide
    leads; states follow A-Z; channels whose feed says nothing land in
    Nationwide rather than in a mystery bucket.
    """
    wanted = str(code or "").strip()
    national = 0
    states: dict[str, tuple[str, int]] = {}
    for row in fetch_rows(safe_mode=safe_mode):
        if row.get("country_code") != wanted:
            continue
        state = str(row.get("state") or "")
        if state:
            name = str(row.get("state_name") or state)
            held = states.get(state)
            states[state] = (name, (held[1] if held else 0) + 1)
        else:
            national += 1
    if not states:
        return []
    out: list[tuple[str, str, int]] = [("national", "Nationwide", national)]
    out.extend(
        sorted(
            ((code_, name, count) for code_, (name, count) in states.items()),
            key=lambda entry: natural_key(entry[1]),
        )
    )
    return out


def area_channels(country: str, area: str, *, safe_mode: bool = False) -> list[RadioStation]:
    """One area's channels: ``area`` is ``"national"`` or a subdivision code.

    A city channel says its city in the details (the note leads with it), so a
    state list still answers "which of these is mine".
    """
    wanted_country = str(country or "").strip()
    wanted_area = str(area or "").strip()
    out: list[RadioStation] = []
    for row in fetch_rows(safe_mode=safe_mode):
        if row.get("country_code") != wanted_country:
            continue
        state = str(row.get("state") or "")
        if wanted_area == "national":
            if state:
                continue
        elif state != wanted_area:
            continue
        city = str(row.get("city") or "")
        guide = _guide_note(str(row.get("id") or ""))
        note = f"{city}. {guide}".strip() if city else guide
        out.append(to_station(row, now_next=note))
    return out
