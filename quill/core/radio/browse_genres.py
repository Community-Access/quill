"""The browse sources that share the genre protocol, and the one handler for them.

Extracted from :mod:`quill.core.radio.browse_sources` under GATE-11 when two
networks joined (2026-10-25). A source module that offers ``fetch_genres``,
``genre_display`` and ``fetch_genre_stations`` becomes a Browse branch -- genres,
then stations -- with one entry in :data:`GENRE_MODULES` and no handler of its
own. That is how Radio Browser's genres, the Community M3U catalog, the Xiph
directory, 181.FM and laut.fm are all browsed by the same five lines.

wx-free; each source keeps its own Safe Mode refusal and reviewed egress site.
"""

from __future__ import annotations

from types import ModuleType

from quill.core.radio import laut_fm, m3u_catalog, one_eighty_one, radio_browser, xiph
from quill.core.radio.browse_nodes import BrowseNode, folder, leaf, make_id

#: Branch kind -> the source module that answers the genre protocol.
GENRE_MODULES: dict[str, ModuleType] = {
    "rbgenre": radio_browser,
    "m3u": m3u_catalog,
    "xiph": xiph,
    "one81": one_eighty_one,
    "lautfm": laut_fm,
}


def browse_genre_source(kind: str, args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A genre source's branch: its genres, or one genre's stations."""
    module = GENRE_MODULES[kind]
    if args and args[0]:
        return [
            leaf(station) for station in module.fetch_genre_stations(args[0], safe_mode=safe_mode)
        ]
    return [
        folder(make_id(kind, slug), module.genre_display(slug))
        for slug in module.fetch_genres(safe_mode=safe_mode)
    ]
