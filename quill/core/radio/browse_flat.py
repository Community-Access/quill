"""The Browse branches that are one flat list of stations, by branch id.

Extracted from :mod:`quill.core.radio.browse_sources` under GATE-11 when the
Westwood One Sports branch arrived (2026-09-28): a flat branch is one line
here and nothing else, so this table is where they grow. Each value takes
``safe_mode`` and returns the branch's stations; the bundled ones (ACB Media,
NFB Radio, Westwood One Sports) ignore it because they make no network call.

``LOCAL_SOURCES`` lives here too (moved from browse_sources.py on 2026-09-29,
when Double Tap Live arrived and that module was at its ratchet): the branches
that work with no network at all, so Safe Mode leaves them alone.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.radio import (
    acb_media,
    double_tap,
    nfb_media,
    radio_browser,
    radio_paradise,
    reading_services,
    soma_fm,
    westwood_one,
)
from quill.core.radio.models import RadioStation

__all__ = ["FLAT", "LOCAL_SOURCES"]

#: Branches that work with no network at all, so Safe Mode leaves them alone.
LOCAL_SOURCES = frozenset({
    "favorites",
    "acb",
    "doubletap",
    "nfb",
    "westwood",
    "networks",
    "networkgroup",
    # The lists themselves are local; only opening one reaches the network.
    "myservers",
    "youtube",
    # Files on this computer: nothing to fetch, so Safe Mode leaves them be.
    "localmedia",
    "localplaylist",
})

FLAT: dict[str, Callable[[bool], list[RadioStation]]] = {
    "popular": lambda safe: radio_browser.popular_stations(safe_mode=safe),
    "trending": lambda safe: radio_browser.trending_stations(safe_mode=safe),
    "recent": lambda safe: radio_browser.recently_changed_stations(safe_mode=safe),
    "acb": lambda _safe: acb_media.acb_media_stations(),
    "doubletap": lambda _safe: double_tap.double_tap_stations(),
    "nfb": lambda _safe: nfb_media.nfb_media_stations(),
    "westwood": lambda _safe: westwood_one.westwood_one_stations(),
    "reading": lambda safe: reading_services.list_reading_services(safe_mode=safe),
    "soma": lambda safe: soma_fm.search_stations("", safe_mode=safe),
    "radioparadise": lambda safe: radio_paradise.fetch_stations(safe_mode=safe),
}
