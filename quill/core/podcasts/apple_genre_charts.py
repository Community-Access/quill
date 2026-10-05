"""Apple's top podcasts *within one genre* -- the chart a genre folder needs.

The browse tree's genre folders used to be filled by taking the storefront's
overall top 100 and keeping the rows tagged with the genre. That reads as
reasonable and answers almost nothing: the overall chart is dominated by news,
comedy and true crime, so History came back with four shows, and a subgenre
such as Comedy Fiction usually came back with none at all -- a folder saying
"Nothing in here" about a genre Apple lists hundreds of shows in (reported
2026-10-03).

Apple publishes a chart per genre, and has for years: the store RSS feed at
``itunes.apple.com/<storefront>/rss/toppodcasts/limit=<n>/genre=<id>/json``
serves up to 200 shows for any genre or subgenre id from the genre tree,
keyless. Checked live on 2026-10-03: History (1487) and Comedy Fiction (1486)
each returned 200 rows.

One request per genre rather than one per storefront, which is the price of a
folder that holds what it says it holds; each answer is cached for hours
through :mod:`quill.core.radio.directory_cache`, so reopening a genre costs
nothing. The request goes through :func:`apple_podcasts._fetch`, the single
reviewed Apple egress site, and refuses in Safe Mode like everything else
there. wx-free, strict-typed.
"""

from __future__ import annotations

import json
import urllib.parse

from quill.core.podcasts import apple_podcasts as apple
from quill.core.radio import directory_cache

#: Apple's per-genre chart. ``limit`` tops out at 200.
GENRE_CHART_URL = (
    "https://itunes.apple.com/{storefront}/rss/toppodcasts/limit={count}/genre={genre}/json"
)

#: How many shows a genre folder asks for: everything Apple will give.
GENRE_CHART_COUNT = 200
_MAX_COUNT = 200

#: Charts change daily; a few hours is fresh enough, and Refresh skips it.
_GENRE_CHART_MAX_AGE = 6 * 3600


def _label(value: object) -> str:
    """``{"label": "x"}`` -> ``"x"``; anything else -> ``""`` (pure)."""
    if isinstance(value, dict):
        return str(value.get("label", "") or "").strip()
    return ""


def _attributes(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        attributes = value.get("attributes")
        if isinstance(attributes, dict):
            return attributes
    return {}


def _entry_to_show(entry: object) -> apple.AppleShow | None:
    """One feed ``entry`` as an :class:`AppleShow`, or ``None`` (pure)."""
    if not isinstance(entry, dict):
        return None
    collection_id = str(_attributes(entry.get("id")).get("im:id", "") or "").strip()
    name = _label(entry.get("im:name"))
    if not collection_id or not name:
        return None
    images = entry.get("im:image")
    artwork = _label(images[-1]) if isinstance(images, list) and images else ""
    genre = str(_attributes(entry.get("category")).get("im:id", "") or "").strip()
    page = str(_attributes(entry.get("link")).get("href", "") or "").strip()
    return apple.AppleShow(
        collection_id=collection_id,
        name=name,
        artist=_label(entry.get("im:artist")),
        artwork_url=artwork,
        page_url=page or _label(entry.get("id")),
        genre_ids=(genre,) if genre else (),
    )


def parse_genre_chart(json_text: str) -> list[apple.AppleShow]:
    """A per-genre chart document into shows, in chart order (pure, total).

    ``entry`` is a list normally and a bare object when the chart has one row
    -- the feed is a JSON rendering of Atom, and Atom does not distinguish --
    so both are read. A chart with no rows has no ``entry`` at all.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return []
    feed = data.get("feed") if isinstance(data, dict) else None
    entries = feed.get("entry") if isinstance(feed, dict) else None
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        return []
    shows: list[apple.AppleShow] = []
    seen: set[str] = set()
    for entry in entries:
        show = _entry_to_show(entry)
        if show is not None and show.collection_id not in seen:
            seen.add(show.collection_id)
            shows.append(show)
    return shows


def fetch_genre_chart(
    storefront: str,
    genre_id: str,
    *,
    count: int = GENRE_CHART_COUNT,
    safe_mode: bool = False,
    refresh: bool = False,
) -> list[apple.AppleShow]:
    """The top shows in one genre (or subgenre) of *storefront*.

    Never raises for a source problem: a failure leaves a stale cached chart if
    there is one, and otherwise an empty list with the failure recorded for the
    browse tree to explain (``directory_cache.resolve``).
    """
    apple.refuse_in_safe_mode(safe_mode)
    genre = genre_id.strip()
    if not genre.isdigit():
        return []
    rows = max(1, min(int(count or GENRE_CHART_COUNT), _MAX_COUNT))
    code = storefront.strip().lower() or "us"
    url = GENRE_CHART_URL.format(storefront=urllib.parse.quote(code), count=rows, genre=genre)
    payload, _age = directory_cache.resolve(
        f"apple:genrechart:{code}:{genre}:{rows}",
        lambda: apple._shows_as_json(parse_genre_chart(apple._fetch(url))),
        max_age_seconds=_GENRE_CHART_MAX_AGE,
        refresh=refresh,
        empty=[],
    )
    return apple._shows_from_json(payload)
