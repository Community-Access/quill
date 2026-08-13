"""Which directories Find Stations searches, and which the listener wants.

One search fans out across a lot of places -- RadioBrowser, TuneIn, iHeart,
SomaFM, NOAA Weather Radio, Radio Reading Services, Spotify, YouTube. That
breadth is the point for someone hunting a station, and it is the problem for
someone who already knows what they want: a listener who only ever wants their
local NPR affiliate does not want eight YouTube videos first, and a listener
without a Spotify account does not want to be reminded of it every search.

So every source can be switched off. Two consequences that shape everything
here:

* **A source that is off is never contacted.** This is not a display filter
  over results that were fetched anyway -- turning off iHeart means iHeart's
  network round trips do not happen, so switching sources off makes searching
  faster as well as quieter. The audit-relevant version: egress follows the
  toggles.
* **The choice is remembered**, alongside the Source facet, because a
  preference you have to re-set on every search is not a preference.

The registry lives here, wx-free and shared, so the browser, the settings
dialog, and the persisted history cannot drift into disagreeing about what the
sources are or what they are called.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchSource:
    """One searchable directory."""

    id: str
    #: The Source-facet label, matching ``RadioStation.source`` where the
    #: source sets one (so filtering and toggling speak the same words).
    label: str
    #: One line on what this source is, for the settings list.
    description: str
    #: Whether it is searched by default. Everything broad is on; the two
    #: account/consent-gated sources are on too, because they are inert until
    #: you have connected them -- they simply return nothing.
    default_on: bool = True
    #: True when the source reaches the network. NOAA and Reading Services
    #: fall back to bundled snapshots, so they still work in Safe Mode.
    network: bool = True


#: Every source Find Stations can search, in the order the settings list shows
#: them: the broad directories first, then the specialised ones, then the two
#: that need an account or a consent.
SEARCH_SOURCES: tuple[SearchSource, ...] = (
    SearchSource(
        "radio_browser",
        "Radio Browser",
        "The community directory behind most of Quill Radio's results.",
    ),
    SearchSource("tunein", "TuneIn", "TuneIn's station directory."),
    SearchSource("iheart", "iHeart", "iHeartRadio's stations."),
    SearchSource("somafm", "SomaFM", "SomaFM's listener-supported channels."),
    SearchSource(
        "wxindex",
        "NOAA Weather Radio",
        "US weather radio, by SAME code, callsign, county or state.",
        network=False,
    ),
    SearchSource(
        "reading_services",
        "Radio Reading Service",
        "Reading services that broadcast newspapers and magazines aloud.",
        network=False,
    ),
    SearchSource(
        "spotify",
        "Spotify",
        "Songs, shows and episodes. Needs a connected Spotify account.",
    ),
    SearchSource(
        "youtube",
        "YouTube",
        "Videos, added as stations you can play and record.",
    ),
)

SOURCE_IDS: tuple[str, ...] = tuple(s.id for s in SEARCH_SOURCES)

#: Everything on: the out-of-the-box behaviour, and what a reset returns to.
DEFAULT_ENABLED: tuple[str, ...] = tuple(s.id for s in SEARCH_SOURCES if s.default_on)

_BY_ID = {s.id: s for s in SEARCH_SOURCES}


def source(source_id: str) -> SearchSource | None:
    """The source with this id, or ``None``."""
    return _BY_ID.get(str(source_id or "").strip().lower())


def label(source_id: str) -> str:
    """The display name for *source_id* (the id itself if unknown)."""
    found = source(source_id)
    return found.label if found is not None else str(source_id)


def normalize(values: object) -> tuple[str, ...]:
    """Clean a stored selection into known ids, in registry order.

    Unknown ids are dropped rather than kept, so a source removed in a later
    build cannot linger. A stored value that is missing or unusable means "not
    configured yet" and gets the defaults -- but an *explicitly empty*
    selection is preserved, because turning everything off is a real choice a
    listener can make, and quietly re-enabling all of it would be a bug.
    """
    if values is None or isinstance(values, (str, bytes)):
        return DEFAULT_ENABLED
    if not isinstance(values, Iterable):
        return DEFAULT_ENABLED
    try:
        wanted = {str(v).strip().lower() for v in values}
    except TypeError:
        return DEFAULT_ENABLED
    return tuple(s.id for s in SEARCH_SOURCES if s.id in wanted)


def is_enabled(enabled: object, source_id: str) -> bool:
    """Whether *source_id* should be searched, given a stored selection.

    An unknown source id answers ``True``: a source this build knows about but
    the stored selection predates must search rather than silently vanish.
    """
    if source(source_id) is None:
        return True
    return source_id in set(normalize(enabled))


def toggle(enabled: object, source_id: str) -> tuple[str, ...]:
    """The selection with *source_id* flipped on or off."""
    current = set(normalize(enabled))
    if source(source_id) is None:
        return normalize(enabled)
    if source_id in current:
        current.discard(source_id)
    else:
        current.add(source_id)
    return tuple(s.id for s in SEARCH_SOURCES if s.id in current)


def describe_selection(enabled: object) -> str:
    """A spoken summary of what a search will cover.

    Named rather than counted when the list is short, because "3 sources" is
    not an answer to "am I searching Spotify?".
    """
    chosen = normalize(enabled)
    if not chosen:
        return "No search sources are switched on, so searching will find nothing."
    if len(chosen) == len(SEARCH_SOURCES):
        return "Searching all sources."
    names = [label(s) for s in chosen]
    if len(names) <= 3:
        return f"Searching {', '.join(names)}."
    return f"Searching {len(names)} of {len(SEARCH_SOURCES)} sources: {', '.join(names)}."
