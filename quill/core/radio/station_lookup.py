"""Finding a station by what is known about it, not only by what it is called.

A search used to match a station's name and its directory tags. That finds
"97.1 The Ticket" when you type "Ticket" and never when you type "Tigers", which
is the word anybody looking for a ball game actually types. Two more things are
now searched, everywhere a station search happens:

* **Your own tags** (:mod:`quill.core.radio.station_tags`) -- whatever you told
  the app about a station.
* **The flagship list** (:mod:`quill.core.radio.sports_flagships`) -- which
  station each major-league team names as its radio home.

A row found either way says *why* in the row itself ("carries the Detroit
Tigers", "has your tag Red Wings"), because a result whose name shares no word
with what you typed otherwise looks like a mistake.

Two callers. The Favorites filter (:func:`search_favorites`, behind
``RadioFavoritesStore.search``) answers from your own list and never leaves the
machine. The station searches (:func:`lane_rows`) also have to turn a flagship's
call sign into something playable, so they hand in a *find* function -- the
local catalog first, the directory after -- which is what keeps this module
free of network code and testable with a lambda.

wx-free, strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from quill.core.radio import sports_flagships
from quill.core.radio.models import RadioStation
from quill.core.radio.sports_flagships import FlagshipStation, Team
from quill.core.radio.station_tags import StationTagStore, tagged_stations

if TYPE_CHECKING:
    from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore

__all__ = [
    "MAX_FLAGSHIP_LOOKUPS",
    "favorite_label",
    "favorite_reason",
    "flagship_rows",
    "lane_rows",
    "own_tag_rows",
    "search_favorites",
    "tag_reason",
]

#: At most this many flagship stations are looked up per search. "MLB" alone
#: names thirty; past a dozen the list is long enough to arrow, and every
#: lookup is a moment somebody spends waiting.
MAX_FLAGSHIP_LOOKUPS = 24

#: Directory rows kept per flagship: the station and, at most, one more mount.
_ROWS_PER_FLAGSHIP = 2


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").casefold())


def _matches_text(query: str, text: str) -> bool:
    """The whole query as typed, or every word of it, appears in *text*."""
    needle = query.strip().casefold()
    hay = text.casefold()
    if not needle:
        return False
    if needle in hay:
        return True
    words = set(_words(hay))
    wanted = _words(needle)
    return bool(wanted) and all(word in words for word in wanted)


def tag_reason(tags: tuple[str, ...], query: str) -> str:
    """ "has your tag Red Wings" for the first of *tags* the query found, or ""."""
    for tag in tags:
        if _matches_text(query, tag):
            return f"has your tag {tag}"
    if tags and _matches_text(query, " ".join(tags)):
        return f"has your tags {', '.join(tags)}"
    return ""


def _teams_by_station(teams: list[Team]) -> list[tuple[FlagshipStation, list[Team]]]:
    """Each flagship station once, with every matched team it carries."""
    grouped: dict[str, tuple[FlagshipStation, list[Team]]] = {}
    for team in teams:
        for station in team.stations:
            key = station.call_base or station.name.casefold()
            if key in grouped:
                grouped[key][1].append(team)
            else:
                grouped[key] = (station, [team])
    return list(grouped.values())


def _flagship_reason(station: object, teams: list[Team]) -> str:
    carried = [
        team
        for team in teams
        if any(sports_flagships.station_matches(station, fs) for fs in team.stations)
    ]
    return sports_flagships.reason_for(carried)


# -- the Favorites filter --------------------------------------------------------


def favorite_reason(favorite: FavoriteStation, query: str, teams: list[Team] | None = None) -> str:
    """Why *favorite* matched *query* when its name may not say: a team it
    carries, or one of your tags. ``""`` when the name or folder already does."""
    if not query.strip():
        return ""
    found = sports_flagships.teams_matching(query) if teams is None else teams
    reason = _flagship_reason(favorite.station, found) if found else ""
    return reason or tag_reason(favorite.user_tags, query)


def search_favorites(store: RadioFavoritesStore, query: str) -> list[FavoriteStation]:
    """Favorites matching *query*, in stored order. Empty returns everything.

    The name, your name for it, country, language, the directory's tags and
    yours, folder and homepage -- the whole query as typed or every word of it
    -- and, failing those, the teams the station carries.
    """
    if not query.strip():
        return list(store.favorites)
    teams = sports_flagships.teams_matching(query)
    out: list[FavoriteStation] = []
    for favorite in store.favorites:
        station = favorite.station
        haystack = " ".join((
            station.name,
            favorite.custom_name,
            station.country,
            station.language,
            " ".join(station.tags),
            " ".join(favorite.user_tags),
            favorite.folder,
            station.homepage,
        ))
        if _matches_text(query, haystack) or (teams and _flagship_reason(station, teams)):
            out.append(favorite)
    return out


def favorite_label(favorite: FavoriteStation, query: str) -> str:
    """A filtered row's label: name, why it matched, and the folder it is in."""
    label = favorite.display_label
    reason = favorite_reason(favorite, query)
    if reason:
        label += f" -- {reason}"
    if favorite.folder:
        label += f" -- in {favorite.folder}"
    return label


# -- the station searches ----------------------------------------------------------


def own_tag_rows(
    query: str,
    *,
    favorites: RadioFavoritesStore | None,
    store: StationTagStore | None,
) -> list[RadioStation]:
    """Stations you tagged with something *query* matches, saying which tag."""
    rows: list[RadioStation] = []
    for station, tags in tagged_stations(favorites=favorites, store=store):
        reason = tag_reason(tags, query)
        if reason:
            rows.append(replace(station, match_reason=reason))
    return rows


def flagship_rows(
    query: str,
    *,
    find: Callable[[str], list[RadioStation]],
    teams: list[Team] | None = None,
    max_lookups: int = MAX_FLAGSHIP_LOOKUPS,
) -> list[RadioStation]:
    """Playable rows for the flagship stations of every team *query* names.

    *find* is asked for the call sign, then (if that found nothing that is
    really the station) for the station's name; only rows that
    :func:`sports_flagships.station_matches` accepts are kept, so a search for
    WXYT that also returns "WXYZ Oldies" keeps only WXYT. A *find* that raises
    costs that one station.
    """
    found = sports_flagships.teams_matching(query) if teams is None else teams
    rows: list[RadioStation] = []
    seen: set[str] = set()
    for flagship, carried in _teams_by_station(found)[: max(0, max_lookups)]:
        matched: list[RadioStation] = []
        for text in dict.fromkeys(t for t in (flagship.call_base, flagship.name) if t):
            try:
                candidates = find(text)
            except Exception:  # noqa: BLE001 - one lookup never sinks the search
                candidates = []
            matched = [c for c in candidates if sports_flagships.station_matches(c, flagship)]
            if matched:
                break
        reason = sports_flagships.reason_for(carried)
        for station in matched[:_ROWS_PER_FLAGSHIP]:
            key = (station.stream_url or station.name).casefold()
            if key in seen:
                continue
            seen.add(key)
            rows.append(replace(station, match_reason=reason))
    return rows


def lane_rows(
    query: str,
    *,
    favorites: RadioFavoritesStore | None,
    store: StationTagStore | None,
    find: Callable[[str], list[RadioStation]],
) -> list[RadioStation]:
    """Your tagged stations, then the flagships, for one station search."""
    if not query.strip():
        return []
    rows = own_tag_rows(query, favorites=favorites, store=store)
    taken = {row.stream_url.casefold() for row in rows}
    rows += [
        row for row in flagship_rows(query, find=find) if row.stream_url.casefold() not in taken
    ]
    return rows
