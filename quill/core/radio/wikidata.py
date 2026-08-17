"""Browse axes no radio directory publishes, derived from Wikidata.

Radio directories know a station's name and its stream. Wikidata knows what a
station *is*: its call sign, the city it is licensed to, who owns it, which
network it takes, its format, and the frequency it sits on. Joining the two gives
ways in that no directory offers --

    By City                 -> stations licensed to that city
    By Owner                -> everything one company runs
    By Format               -> news, talk, classical, country
    On the Dial             -> by frequency band

There was a fourth axis, **By Network**, and it is gone. Wikidata's
"original broadcaster" (P449) is carried by *two* US radio stations, so the
axis could never have listed anything; it shipped because nobody counted. An
axis that opens to nothing is worse than one not offered -- the listener spends
the keystrokes either way and only one of them can pay off (removed
2026-08-16). "By Format" was pointed at P2360, "intended public", carried by
*zero* stations; it now uses P415, "radio format", carried by 1,715.

"On the Dial" is the one worth arguing for. Browsing by frequency is how radio
worked for a century; it is absent from every internet radio client; and for a
listener who knows their local dial by heart it is the most natural index there
is.

**This is derived, not authoritative, and the code says so everywhere.** Wikidata
contributes the *organisation*; the stream always comes from Radio Browser, so
playback, favourites and recording are unchanged. Five rules keep it honest:

* Off by default, and labelled as derived.
* Matched conservatively -- call sign plus country, or an exact name plus
  country. A fuzzy match that offers the wrong station is worse than a short
  list, and far worse than no list.
* Cached persistently with its age available, because a SPARQL query per expand
  is not acceptable and staleness must be visible rather than assumed.
* Degrades to absent: if Wikidata is unreachable the branch says so once and the
  rest of the tree is untouched.
* One request per level, on an endpoint that asks for a descriptive User-Agent
  and gets one.

One reviewed egress site (:func:`_fetch`), HTTPS-only over a verified TLS
context, Safe Mode gated. wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.radio import directory_cache, radio_browser
from quill.core.radio.models import RadioStation

_USER_AGENT = f"QUILL-Radio/{__version__} (+https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 45.0
_MAX_BYTES = 8_000_000
_ENDPOINT = "https://query.wikidata.org/sparql"

#: Wikidata's own rate guidance is generous but a SPARQL query is expensive for
#: them; a week is plenty for facts that change when a station is sold.
_MAX_AGE_SECONDS = 7 * 24 * 3600

#: How many rows one axis returns. Enough to be a real list, small enough that
#: the query completes inside the timeout.
_LIMIT = 400

#: The axes offered, as ``(id, label, the Wikidata property behind it)``.
AXES: tuple[tuple[str, str, str], ...] = (
    ("city", "By City", "P131"),
    ("owner", "By Owner", "P127"),
    ("format", "By Format", "P415"),
)

#: FM band slices for "On the Dial", in MHz.
DIAL_BANDS: tuple[tuple[str, float, float], ...] = (
    ("87 to 91 MHz", 87.0, 91.0),
    ("91 to 95 MHz", 91.0, 95.0),
    ("95 to 99 MHz", 95.0, 99.0),
    ("99 to 103 MHz", 99.0, 103.0),
    ("103 to 108 MHz", 103.0, 108.1),
)


class WikidataError(CodedError):
    """A Wikidata query failed (network, or Safe Mode refusal)."""

    code = "QUILL-RADIO-WIKIDATA-QUERY"


@dataclass(frozen=True, slots=True)
class WikidataStation:
    """One station as Wikidata describes it. Not playable on its own."""

    call_sign: str
    name: str
    grouping: str = ""
    frequency_mhz: float = 0.0
    country: str = ""


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`WikidataError` when Safe Mode is active."""
    if safe_mode:
        raise WikidataError(
            "Explore (Wikidata) is disabled in Safe Mode. Restart QUILL normally to use it."
        )


def _fetch(query: str) -> str:
    """One SPARQL GET -- the reviewed egress site."""
    url = f"{_ENDPOINT}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/sparql-results+json"}
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
        raise WikidataError(f"Could not reach Wikidata: {error}") from error
    return payload.decode("utf-8", errors="replace")


def _query(grouping_property: str, country_qid: str) -> str:
    """A SPARQL query for stations grouped by one property (pure).

    ``wdt:P31/wdt:P279*`` walks the subclass tree so "radio station" catches the
    many specific kinds beneath it. Only stations with a call sign are taken --
    it is the identifier the conservative match depends on.

    **The grouping property is required, not optional.** It was optional, and
    because the query takes an arbitrary ``LIMIT`` slice of tens of thousands
    of stations, most of that slice had no value for the property being grouped
    by: "By Network" and "By Format" returned 400 stations and *zero* groups,
    so both folders were simply empty (found 2026-08-16 while fixing the place
    axis). A station with no network is not a station this axis can file.
    """
    return f"""
SELECT ?callsign ?stationLabel ?groupLabel ?freq WHERE {{
  ?station wdt:P31/wdt:P279* wd:Q14350 ;
           wdt:P17 wd:{country_qid} ;
           wdt:P2317 ?callsign ;
           wdt:{grouping_property} ?group .
  OPTIONAL {{ ?station wdt:P2144 ?freq }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
}}
LIMIT {_LIMIT}
""".strip()


def parse_results(json_text: str) -> list[WikidataStation]:
    """SPARQL JSON into :class:`WikidataStation` (pure).

    Frequencies arrive in hertz and are converted to MHz; a value outside the FM
    band is discarded rather than shown, because Wikidata carries AM stations in
    the same field and 1010 kHz is not a dial position anyone browses in MHz.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    bindings = ((data.get("results") or {}).get("bindings")) if isinstance(data, dict) else None
    stations: list[WikidataStation] = []
    for row in bindings if isinstance(bindings, list) else []:
        if not isinstance(row, dict):
            continue
        call_sign = str((row.get("callsign") or {}).get("value", "")).strip()
        name = str((row.get("stationLabel") or {}).get("value", "")).strip()
        if not call_sign:
            continue
        frequency = 0.0
        raw = (row.get("freq") or {}).get("value")
        if raw:
            try:
                hertz = float(raw)
            except (TypeError, ValueError):
                hertz = 0.0
            megahertz = hertz / 1_000_000 if hertz > 1_000_000 else hertz
            frequency = megahertz if 87.0 <= megahertz <= 108.1 else 0.0
        stations.append(
            WikidataStation(
                call_sign=call_sign,
                name=name or call_sign,
                grouping=str((row.get("groupLabel") or {}).get("value", "")).strip(),
                frequency_mhz=frequency,
            )
        )
    return stations


def stations_for_axis(
    axis: str, country_qid: str = "Q30", *, safe_mode: bool = False, refresh: bool = False
) -> list[WikidataStation]:
    """Every station Wikidata knows, carrying the grouping for *axis*."""
    refuse_in_safe_mode(safe_mode)
    prop = next((p for key, _label, p in AXES if key == axis), "")
    if not prop:
        return []
    payload, _age = directory_cache.resolve(
        # The property is part of the key: when "By Format" moved off P2360
        # (which no station carries) onto P415, every existing install would
        # otherwise have kept serving the empty answer until the cache aged
        # out. Keyed this way, correcting a property invalidates it for free.
        f"wikidata:{axis}:{prop}:{country_qid}",
        lambda: [
            {
                "cs": s.call_sign,
                "n": s.name,
                "g": s.grouping,
                "f": s.frequency_mhz,
            }
            for s in parse_results(_fetch(_query(prop, country_qid)))
        ],
        max_age_seconds=_MAX_AGE_SECONDS,
        refresh=refresh,
        empty=[],
    )
    return [
        WikidataStation(
            call_sign=str(row.get("cs", "")),
            name=str(row.get("n", "")),
            grouping=str(row.get("g", "")),
            frequency_mhz=float(row.get("f") or 0.0),
        )
        for row in payload
        if isinstance(row, dict) and row.get("cs")
    ]


def groupings(stations: list[WikidataStation]) -> list[tuple[str, int]]:
    """The distinct groupings and how many stations each holds (pure).

    **Sorted A to Z.** It was sorted by size first, which reads well on a
    screen -- biggest cities at the top -- and badly by ear: a listener
    hunting for Tucson in a hundred cities has to know how big Tucson is
    before they know where to arrow to. Alphabetical is the order you can
    predict without knowing the data, and the counts still ride along.

    Groupings with a single station are kept: a one-station city is still that
    city, and hiding it would make the axis quietly incomplete.
    """
    counts: dict[str, int] = {}
    for station in stations:
        if station.grouping:
            counts[station.grouping] = counts.get(station.grouping, 0) + 1
    return sorted(counts.items(), key=lambda row: row[0].casefold())


def band_of(frequency_mhz: float) -> str:
    """Which dial band a frequency falls in (pure), or ``""``."""
    for label, low, high in DIAL_BANDS:
        if low <= frequency_mhz < high:
            return label
    return ""


def stations_in_place(
    place: str, *, limit: int = 200, safe_mode: bool = False
) -> list[RadioStation]:
    """Every station Radio Browser files under *place*, most-listened first.

    The place axis used to work the wrong way round: take Wikidata's list of
    stations for a place, then look each one up. Wikidata's query is capped
    (``_LIMIT``) and unordered, so that list is an arbitrary slice of tens of
    thousands of stations -- and for Arizona the twelve it happened to return
    were twelve Radio Browser does not carry, so the folder opened to nothing
    while KJZZ, KBAQ and forty-seven others sat there playable (reported
    2026-08-16: "Arizona is showing none that can be played while I know of at
    least one").

    Asking Radio Browser for the place directly starts from the set that can
    actually play. ``state`` is the field US stations are filed under; when it
    matches nothing -- a city, or a place Radio Browser spells differently --
    the name search is the second try.
    """
    wanted = place.strip()
    if not wanted:
        return []
    try:
        found = radio_browser.search_stations(state=wanted, limit=limit, safe_mode=safe_mode)
    except Exception:  # noqa: BLE001 - a miss here must not empty the folder
        found = []
    if found:
        return found
    try:
        return radio_browser.search_stations(wanted, limit=limit, safe_mode=safe_mode)
    except Exception:  # noqa: BLE001
        return []


def stations_with_format(
    fmt: str, *, limit: int = 200, safe_mode: bool = False
) -> list[RadioStation]:
    """Stations Radio Browser tags with *fmt*.

    Wikidata's format names ("Active rock", "Christian radio") and Radio
    Browser's tags ("rock", "christian") are the same vocabulary spelled
    differently, in two ways that both had to be handled: **Radio Browser's
    tags are lower case and match exactly** -- "Christian" returns nothing
    where "christian" returns hundreds -- and the useful word is sometimes the
    last ("Active rock" -> "rock") and sometimes the first ("Christian radio"
    -> "christian"). So the whole name is tried, then the last word, then the
    first. Anything found tops up the call-sign matches rather than replacing
    them.
    """
    wanted = fmt.strip()
    if not wanted:
        return []
    words = [w.strip("-,") for w in wanted.casefold().split() if w.strip("-,")]
    attempts: list[str] = []
    for candidate in (wanted.casefold(), *(reversed(words) if words else ())):
        if candidate and candidate not in attempts:
            attempts.append(candidate)
    for attempt in attempts:
        try:
            found = radio_browser.search_stations(tag=attempt, limit=limit, safe_mode=safe_mode)
        except Exception:  # noqa: BLE001 - a miss must not empty the folder
            continue
        if found:
            return found
    return []


def playable(
    stations: list[WikidataStation], *, country: str = "", safe_mode: bool = False
) -> list[RadioStation]:
    """Match Wikidata stations to playable ones, conservatively.

    Call sign plus country only. A station Radio Browser does not carry is simply
    absent -- offering a row that cannot play, or worse a *different* station
    with a similar name, is the failure mode this whole branch has to avoid.
    Every returned row is an ordinary Radio Browser station, so playback,
    favourites and recording are untouched.
    """
    found: list[RadioStation] = []
    seen: set[str] = set()
    for station in stations:
        try:
            matches = radio_browser.search_stations(
                station.call_sign, country=country, limit=5, safe_mode=safe_mode
            )
        except Exception:  # noqa: BLE001 - one miss must not end the list
            continue
        wanted = station.call_sign.casefold()
        for candidate in matches:
            name = (candidate.name or "").casefold()
            # The call sign must appear as a word, not as a fragment inside
            # another name: "KJZZ" must not match "Radio KJZZLAND".
            if wanted in name.replace("-", " ").split() or name.startswith(wanted):
                if candidate.stream_url not in seen:
                    seen.add(candidate.stream_url)
                    found.append(candidate)
                break
    return found
