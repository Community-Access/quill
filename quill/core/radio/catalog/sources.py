"""The Class-A source specs: what refreshes, and how each page is shaped.

Only sources whose licenses permit local storage appear here - that is the
whole point of the classing. Everything fetches through its source module's
existing reviewed egress chokepoint; this module adds no network call sites
of its own, it only maps payloads to :class:`StationRow`.
"""

from __future__ import annotations

from collections.abc import Iterator

from quill.core.radio.catalog.keys import canonical_key, normalize_stream_url
from quill.core.radio.catalog.refresh import SourceSpec
from quill.core.radio.catalog.store import StationRow

#: One dump page. 10k rows keeps refresh memory in the tens of megabytes
#: (whole-dump loading measured 217 MB).
PAGE_SIZE = 10_000

#: Politeness gap between dump pages, seconds.
PAGE_GAP_SECONDS = 0.5


def _normalize_tags(raw: object) -> str:
    text = raw if isinstance(raw, str) else ""
    seen: list[str] = []
    for tag in text.split(","):
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return ",".join(seen)[:300]


def _as_int(value: object) -> int:
    try:
        return int(str(value or 0))
    except (TypeError, ValueError):
        return 0


def row_from_radio_browser(entry: dict[str, object]) -> StationRow | None:
    """One Radio Browser record as a catalog row (pure)."""
    uuid = str(entry.get("stationuuid") or "")
    url = str(entry.get("url_resolved") or entry.get("url") or "").strip()
    name = " ".join(str(entry.get("name") or "").split())[:200]
    if not url or not name:
        return None
    bitrate = _as_int(entry.get("bitrate"))
    votes = _as_int(entry.get("votes"))
    return StationRow(
        key=canonical_key(uuid, url),
        name=name,
        stream_url=url,
        homepage=str(entry.get("homepage") or "").strip(),
        favicon=str(entry.get("favicon") or "").strip(),
        country=str(entry.get("country") or "").strip(),
        state=str(entry.get("state") or "").strip(),
        language=str(entry.get("language") or "").strip().lower(),
        tags=_normalize_tags(entry.get("tags")),
        codec=str(entry.get("codec") or "").strip().upper(),
        bitrate=bitrate,
        votes=votes,
        source_id="radio_browser",
        source_record_id=uuid,
    )


def _radio_browser_pages() -> Iterator[list[StationRow]]:
    import time

    from quill.core.radio import radio_browser

    offset = 0
    while True:
        raw = radio_browser.fetch_station_page(offset, PAGE_SIZE)
        rows = [row for row in (row_from_radio_browser(e) for e in raw) if row is not None]
        if rows:
            yield rows
        if len(raw) < PAGE_SIZE:
            return
        offset += PAGE_SIZE
        time.sleep(PAGE_GAP_SECONDS)


def _soma_pages() -> Iterator[list[StationRow]]:
    from quill.core.radio import soma_fm

    stations = soma_fm.search_stations("")
    rows = [
        StationRow(
            key=canonical_key(station.station_uuid, station.stream_url),
            name=station.name,
            stream_url=station.stream_url,
            homepage=station.homepage,
            favicon=station.favicon,
            country=station.country,
            language=station.language,
            tags=_normalize_tags(",".join(station.tags)),
            codec=station.codec,
            bitrate=station.bitrate_kbps,
            votes=station.votes,
            source_id="soma_fm",
            source_record_id=station.station_uuid,
        )
        for station in stations
    ]
    if rows:
        yield rows


def _xiph_pages() -> Iterator[list[StationRow]]:
    """Xiph, for when its backend recovers. The refresh engine's empty-guard
    is what makes it safe to keep asking while it is down."""
    from quill.core.radio import xiph

    for genre in xiph.fetch_genres():
        page = [
            StationRow(
                key=canonical_key("", normalize_stream_url(station.stream_url)),
                name=station.name,
                stream_url=station.stream_url,
                homepage=station.homepage,
                country=station.country,
                language=station.language,
                tags=_normalize_tags(",".join([genre, *station.tags])),
                codec=station.codec,
                bitrate=station.bitrate_kbps,
                source_id="xiph",
            )
            for station in xiph.fetch_genre_stations(genre)
        ]
        if page:
            yield page


def station_specs() -> list[SourceSpec]:
    """Every refreshable station source, in trust order."""
    return [
        SourceSpec("radio_browser", "Radio Browser", _radio_browser_pages),
        SourceSpec("soma_fm", "SomaFM", _soma_pages),
        SourceSpec("xiph", "Xiph", _xiph_pages),
    ]


#: The Choose Browse Sources ids that gate each spec: hiding the branch also
#: stops its refresh (off means never contacted).
VISIBILITY_IDS = {
    "radio_browser": {"popular", "trending", "recent", "rbcountry", "rblang", "rbgenre", "rbcodec"},
    "soma_fm": {"soma"},
    "xiph": {"xiph"},
}


def enabled_spec_ids(visible_source_ids: set[str]) -> set[str]:
    """Which specs may refresh, given the listener's visible branches."""
    return {
        spec_id for spec_id, branches in VISIBILITY_IDS.items() if branches & visible_source_ids
    }
