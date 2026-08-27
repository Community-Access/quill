"""The three station directories added on 2026-08-26, as browse handlers.

Extracted from :mod:`quill.core.radio.browse_sources` under GATE-11 (extract,
never rebaseline) the moment that module reached the ~1000-line decomposition
point its own budget entry names -- the same move ``browse_free_music`` and
``browse_libraries`` already made for their sources.

What lives here is the routing for **SHOUTcast** (its genre tree with the live
Top 500 pinned above it, and the lazy rows that are resolved on play) and
**Live365** (5,000-odd stations grouped A to Z). Radio Paradise needs no handler
at all -- it is a flat list, so it rides the shared ``_FLAT`` table.

Every client stays in its own module (``shoutcast.py``, ``live365.py``); this is
the tree shape and nothing else. wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.radio import iptv, live365, shoutcast
from quill.core.radio.browse_nodes import BrowseNode, action, folder, lazy_leaf, leaf, make_id
from quill.core.radio.models import RadioStation


def shoutcast_rows(stations: Sequence[RadioStation]) -> list[BrowseNode]:
    """SHOUTcast stations as **lazily resolved** leaves.

    A SHOUTcast row's address is a tune-in ``.pls``, and a player is given a
    stream rather than a playlist of one -- so the row carries its id and the
    real address is fetched when it is played (reported 2026-08-26: stations
    that were plainly on the air would not start). Resolving all 500 up front
    would be 500 requests to read one page.
    """
    rows: list[BrowseNode] = []
    for station in stations:
        station_id = shoutcast.station_id_of(station)
        if not station_id:
            rows.append(leaf(station))
            continue
        note = ", ".join(
            part
            for part in (
                f"{station.listeners:,} listening" if station.listeners else "",
                station.notes,
            )
            if part
        )
        rows.append(lazy_leaf(make_id(shoutcast.STATION_KIND, station_id), station.name, note=note))
    return rows


def browse_shoutcast(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """SHOUTcast: Top 500 pinned above the genres, then one genre's stations.

    It is one root rather than two (asked for 2026-08-26). The Top 500 is the
    most useful thing the directory publishes -- the only live audience
    leaderboard in the tree -- so it is the first child rather than a genre
    somewhere under T, and it is still one Enter away from the branch.
    """
    if args and args[0]:
        return shoutcast_rows(shoutcast.fetch_genre_stations(args[0], safe_mode=safe_mode))
    nodes = [folder("shoutcasttop", "Top 500 (most listeners right now)")]
    nodes += [
        folder(make_id("shoutcast", genre), shoutcast.genre_display(genre))
        for genre in shoutcast.fetch_genres(safe_mode=safe_mode)
    ]
    return nodes


def browse_shoutcast_top(_args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The live Top 500, most listeners first. Never cached: a leaderboard
    whose whole value is that it is true right now."""
    return shoutcast_rows(shoutcast.top_stations(safe_mode=safe_mode))


def browse_live365(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Live365: A-Z folders, then that letter's stations.

    Five and a half thousand stations is not a list anybody can work with, least
    of all by ear, so the root is 27 folders. Both levels read the same cached
    sitemap, so opening a letter costs no request at all.
    """
    if args and args[0]:
        return [leaf(s) for s in live365.fetch_letter(args[0], safe_mode=safe_mode)]
    stations = live365.fetch_stations(safe_mode=safe_mode)
    counts: dict[str, int] = {}
    for station in stations:
        letter = live365.letter_of(station.name)
        counts[letter] = counts.get(letter, 0) + 1
    return [
        folder(make_id("live365", letter), letter, child_count=counts[letter])
        for letter in live365.letters()
        if counts.get(letter)
    ]


def browse_tv(_args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Television's front page: the two axes, and the antenna question.

    The antenna row is a deliberate link-out. AntennaWeb (the CTA/NAB
    over-the-air coverage tool) has no published API, and scraping an
    undocumented commercial SPA is exactly what this project's egress policy
    exists to refuse -- the same ruling as Live365's private API. The question
    is real, so the row takes it to the site that answers it, in the browser.
    """
    return [
        folder("tvcountry", "By Country"),
        folder("tvcategory", "By Category"),
        action(
            "tvrefresh",
            "Update the channel list now",
            note="the catalog refreshes itself weekly; this fetches today's",
        ),
        action(
            "antennaweb",
            "Which channels can my antenna receive? (antennaweb.org)",
            note="opens in your browser",
        ),
    ]


def browse_tv_countries(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Countries, then a country's areas where its feeds declare any.

    A country with local broadcasting (the US: ~1,700 channels) opens into
    **Nationwide** plus its states, each state carrying its own and its
    cities' channels; a country whose feeds declare no areas -- most -- stays
    a flat list, because folders with nothing to organise are steps for
    nothing.
    """
    if args and args[0]:
        areas = iptv.country_areas(args[0], safe_mode=safe_mode)
        if areas:
            return [
                folder(make_id("tvarea", args[0], code), label, child_count=count)
                for code, label, count in areas
                if count
            ]
        return [leaf(station) for station in iptv.country_channels(args[0], safe_mode=safe_mode)]
    return [
        folder(make_id("tvcountry", code), name, child_count=count)
        for code, name, count in iptv.countries(safe_mode=safe_mode)
    ]


def browse_tv_area(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """One area's channels: Nationwide, or one state (its cities included)."""
    if len(args) < 2:
        return []
    return [leaf(s) for s in iptv.area_channels(args[0], args[1], safe_mode=safe_mode)]


def browse_tv_categories(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """TV categories, or one category's channels."""
    if args and args[0]:
        return [leaf(station) for station in iptv.category_channels(args[0], safe_mode=safe_mode)]
    return [
        folder(make_id("tvcategory", key), label, child_count=count)
        for key, label, count in iptv.categories(safe_mode=safe_mode)
    ]


# --- Quillin-contributed sources (radio2.md part VIII) ------------------------


def browse_quillins(_args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """One folder per Quillin browse provider. The root only exists when at
    least one is registered -- see ``browse_sources.visible_roots``."""
    from quill.core.radio import directory_registry

    return [
        folder(make_id("extdir", entry.provider_id), entry.display_name)
        for entry in directory_registry.browse_providers()
    ]


def _ext_rows(entry: object, category: str, query: str) -> list[BrowseNode]:
    from quill.core.radio import directory_registry

    rows: list[BrowseNode] = []
    for raw in entry.stations(category, query):  # type: ignore[attr-defined]
        coerced = directory_registry.station_from_row(raw, entry.display_name)  # type: ignore[attr-defined]
        if coerced is None:
            continue
        station, key = coerced
        if key and entry.resolve is None:  # type: ignore[attr-defined]
            # A key with nobody to resolve it is a row that could never play.
            # The provider's own manifest could not declare this shape (the
            # validator ties resolve to stations), but a handler can still
            # emit it, and it is dropped here rather than offered and failed.
            if not station.stream_url:
                continue
            rows.append(leaf(station))
            continue
        if key and entry.resolve is not None:  # type: ignore[attr-defined]
            rows.append(
                lazy_leaf(
                    make_id("extdirstation", entry.provider_id, key),  # type: ignore[attr-defined]
                    station.name,
                    note=station.source,
                )
            )
        else:
            rows.append(leaf(station))
    return rows


def browse_extdir(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A Quillin source's categories, or one category's stations.

    Safe Mode note: the handler itself cannot reach the network directly -- any
    fetch goes through the Quillin host, and Safe Mode disables Quillin
    contributions wholesale before this branch can exist -- so there is no
    per-call refusal here to duplicate that gate.
    """
    from quill.core.radio import directory_registry

    if not args:
        return []
    entry = directory_registry.browse_provider(args[0])
    if entry is None:
        return []
    if len(args) > 1 and args[1]:
        return _ext_rows(entry, args[1], "")
    categories = entry.categories()
    if not categories:
        return _ext_rows(entry, "", "")
    return [folder(make_id("extdir", entry.provider_id, name), name) for name in categories]
