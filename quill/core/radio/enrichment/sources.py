"""Where station facts may come from: the pluggable source interface.

**The data terms are not settled** (Jeff, 2026-10-16), so the rule here is
simple and enforced by structure rather than by good intentions: a source is
used by the pack builder only when it is in :data:`APPROVED_SOURCES`, and the
only approved sources read data this project already ships under terms it
already has:

- ``community_picks`` -- the Community Picks catalogue
  (``quill/core/data/community_picks.json``). Written and curated by the
  project and its listeners for exactly this purpose; it carries the
  descriptions people wrote for the stations they suggested.
- ``station_catalog`` -- a station catalog generation as Radio already builds
  and bundles it (the ``seed.db.xz`` the release ships). It adds **no new
  third-party facts**: only fields the shipped seed already carries (name,
  place, language, tags, home page), plus the call sign and frequency read out
  of the station's own name.

Nothing here fetches anything. No source scrapes, probes a stream, or reads a
web page; a source is handed the files it reads.

**Adding a source once its terms are approved** -- the clearly named place:

1. Write a class with the :class:`EnrichmentSource` shape (``id``, ``title``,
   ``terms``, ``attribution`` and ``records()``), in its own module.
2. Record the decision -- who approved it, when, under which licence, and the
   credit line the licence requires -- in ``terms`` and in the design record
   (``docs/design/2026-10-16-station-pack-format.md``, "Approved sources").
3. Move its entry from :data:`PENDING_SOURCES` to :data:`APPROVED_SOURCES`
   via :func:`approved_source_factories`. A source with network access also
   needs its entry in ``network_egress_audit`` -- it runs in the weekly
   workflow, never on a listener's computer.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from quill.core.radio.catalog.keys import normalize_stream_url
from quill.core.radio.enrichment.facts import StationFacts


@runtime_checkable
class EnrichmentSource(Protocol):
    """One place station facts come from. Read-only, deterministic, offline."""

    #: Stable identifier written into every fact's provenance.
    id: str
    #: The name a listener would recognise, for the details pane.
    title: str
    #: The data terms this source is used under, in one or two sentences.
    terms: str
    #: The credit line its licence requires on every record it supplies, if any.
    attribution: str

    def records(self) -> Iterator[StationFacts]:
        """Every station this source knows something about."""
        ...


@dataclass(frozen=True, slots=True)
class PendingSource:
    """A source somebody has proposed and nobody has approved. Never used."""

    id: str
    title: str
    question: str


#: Proposed in the program plan, awaiting Jeff's decision on the data terms.
#: Listed so the gap is visible in code and in the design record; nothing
#: reads this list to fetch anything.
PENDING_SOURCES: tuple[PendingSource, ...] = (
    PendingSource(
        "radio_browser_enriched",
        "Radio Browser (redistributed enriched copy)",
        "Radio Browser's data terms need confirming before an enriched copy is redistributed.",
    ),
    PendingSource(
        "wikipedia",
        "Wikipedia station articles",
        "CC BY-SA 4.0: the attribution wording and the share-alike obligation "
        "for the summary text need settling.",
    ),
    PendingSource(
        "icy_self_description",
        "What each stream says about itself (ICY headers)",
        "Whether probing every stream weekly is acceptable, and how often.",
    ),
    PendingSource(
        "homepage_meta",
        "Station home page description and keywords",
        "Meta description and keywords only, honouring robots.txt; needs a decision.",
    ),
)


class CommunityPicksSource:
    """The Community Picks catalogue: the project's own, curated descriptions."""

    id = "community_picks"
    title = "QuillVille Community Picks"
    terms = (
        "Curated by the QUILL project and its listeners and shipped with every "
        "build; the project's own data."
    )
    attribution = ""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (Path(__file__).resolve().parents[2] / "data" / "community_picks.json")

    def records(self) -> Iterator[StationFacts]:
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        stamp = str(document.get("updated", ""))[:10] if isinstance(document, dict) else ""
        collections = document.get("collections", []) if isinstance(document, dict) else []
        for collection in collections if isinstance(collections, list) else []:
            group = str(collection.get("title", "")) if isinstance(collection, dict) else ""
            items = collection.get("items", []) if isinstance(collection, dict) else []
            for item in items if isinstance(items, list) else []:
                if not isinstance(item, dict) or item.get("type") != "stream":
                    continue  # podcasts are not stations
                url = str(item.get("stream_url") or "").strip()
                key = normalize_stream_url(url)
                if not key:
                    continue
                yield StationFacts(
                    key=key,
                    name=str(item.get("title") or "").strip(),
                    stream_url=url,
                    description=str(item.get("description") or "").strip(),
                    language=str(item.get("language") or "").strip(),
                    homepage=str(item.get("homepage") or "").strip(),
                    tags=group.lower(),
                    confirmed=str(item.get("added") or stamp),
                )


class StationCatalogSource:
    """A station catalog generation as Radio already builds and ships it.

    Only the fields the shipped seed already carries; the merge then reads the
    call sign and frequency out of each station's own name. No new facts.
    """

    id = "station_catalog"
    title = "Quill Radio station catalog"
    terms = (
        "The station directory data Radio already bundles in its catalog seed, "
        "under the terms it is already shipped; no new facts are added."
    )
    attribution = ""

    def __init__(self, path: Path) -> None:
        self._path = path

    def records(self) -> Iterator[StationFacts]:
        if not self._path.is_file():
            return
        try:
            con = sqlite3.connect(f"file:{self._path.as_posix()}?mode=ro", uri=True)
        except sqlite3.Error:
            return
        try:
            rows = con.execute(
                "SELECT key, name, stream_url, homepage, country, state, language, tags, "
                "last_seen FROM stations WHERE vanished_at IS NULL ORDER BY key"
            ).fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            con.close()
        for key, name, url, homepage, country, state, language, tags, seen in rows:
            yield StationFacts(
                key=str(key),
                name=str(name or ""),
                stream_url=str(url or ""),
                homepage=str(homepage or ""),
                country=str(country or ""),
                state=str(state or ""),
                language=str(language or ""),
                tags=str(tags or ""),
                confirmed=_day(seen),
            )


def _day(epoch: object) -> str:
    """A catalog stamp (epoch seconds as text) as YYYY-MM-DD, or ""."""
    from datetime import UTC, datetime

    try:
        return datetime.fromtimestamp(float(str(epoch)), tz=UTC).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


#: The approved sources, most trusted first, as factories taking the build's
#: inputs. **This is the place an approved source is added** (see the module
#: docstring); a source that is not here is never read.
SourceFactory = Callable[[dict[str, Path]], EnrichmentSource | None]


def _picks(inputs: dict[str, Path]) -> EnrichmentSource | None:
    return CommunityPicksSource(inputs.get("picks"))


def _catalog(inputs: dict[str, Path]) -> EnrichmentSource | None:
    path = inputs.get("catalog")
    return StationCatalogSource(path) if path is not None else None


APPROVED_SOURCES: tuple[tuple[str, SourceFactory], ...] = (
    ("community_picks", _picks),
    ("station_catalog", _catalog),
)


def approved_source_factories() -> tuple[tuple[str, SourceFactory], ...]:
    """The approved sources in trust order. Pending ones are never included."""
    return APPROVED_SOURCES


def build_sources(inputs: dict[str, Path]) -> list[EnrichmentSource]:
    """Instantiate every approved source the build has inputs for."""
    sources: list[EnrichmentSource] = []
    for _source_id, factory in approved_source_factories():
        source = factory(inputs)
        if source is not None:
            sources.append(source)
    return sources


__all__ = [
    "APPROVED_SOURCES",
    "PENDING_SOURCES",
    "CommunityPicksSource",
    "EnrichmentSource",
    "PendingSource",
    "StationCatalogSource",
    "approved_source_factories",
    "build_sources",
]
