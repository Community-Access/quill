"""IPRD in the Browse Stations tree: By Country, By Genre, a hundred at a time.

Its own module so :mod:`quill.core.radio.browse_sources` (at its GATE-11
ratchet) gains one ``HANDLERS`` update and nothing else. The client is
:mod:`quill.core.radio.iprd`; the branch shape follows BlindRadio by serrebidev
(MIT), ``crates/blindradio-core/src/sources/iprd.rs``.

Node ids::

    iprd                                  By Country, By Genre
    iprdcountries | iprdcountry:<country>[\\t<page>]
    iprdgenres    | iprdgenre:<genre>[\\t<page>]

A page number in an id is the "More..." row's: the first page has none, so the
id a listener's browse position remembers is the folder's own. wx-free,
strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio import iprd
from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id
from quill.core.radio.models import RadioStation


def _page_number(args: list[str]) -> int:
    return int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) > 1 else 1


def paged(kind: str, key: str, stations: list[RadioStation], number: int) -> list[BrowseNode]:
    """One page of *stations* as leaves, and a "More..." row when there are more.

    No silent caps: a folder showing 100 of 4,012 says so and offers the rest.
    """
    rows, total = iprd.page(stations, number)
    nodes = [leaf(station) for station in rows]
    shown = (number - 1) * iprd.PAGE_SIZE + len(rows)
    if shown < total:
        nodes.append(
            folder(
                make_id(kind, key, str(number + 1)),
                "More...",
                note=f"showing {shown:,} of {total:,}",
            )
        )
    return nodes


def browse_iprd(_args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The branch's front page. Opening it fetches nothing yet."""
    iprd.refuse_in_safe_mode(safe_mode)
    return [folder("iprdcountries", "By Country"), folder("iprdgenres", "By Genre")]


def browse_countries(_args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Every country with its station count, A to Z."""
    return [
        folder(make_id("iprdcountry", name), name, child_count=count)
        for name, count in iprd.countries(safe_mode=safe_mode)
    ]


def browse_country(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """One country's stations, a page at a time."""
    if not args or not args[0]:
        return []
    stations = iprd.country_stations(args[0], safe_mode=safe_mode)
    return paged("iprdcountry", args[0], stations, _page_number(args))


def browse_genres(_args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The most-used genres with their counts, A to Z."""
    return [
        folder(make_id("iprdgenre", name), name.title(), child_count=count)
        for name, count in iprd.genres(safe_mode=safe_mode)
    ]


def browse_genre(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """One genre's stations, a page at a time."""
    if not args or not args[0]:
        return []
    stations = iprd.genre_stations(args[0], safe_mode=safe_mode)
    return paged("iprdgenre", args[0], stations, _page_number(args))


#: Registered into ``browse_sources._HANDLERS``.
HANDLERS: dict[str, Callable[..., list[BrowseNode]]] = {
    "iprd": browse_iprd,
    "iprdcountries": browse_countries,
    "iprdcountry": browse_country,
    "iprdgenres": browse_genres,
    "iprdgenre": browse_genre,
}
