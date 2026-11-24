"""Beacon places that point into Scribe for Documents results (PRD 8.7, 8.1.7).

A Scribe place is an ordinary Beacon -- a Resource, a Location and the Beacon
itself (PRD 24.1) -- with three things more:

* the Resource remembers the Scribe document in ``provider_ids["scribe"]``
  and the format in ``metadata["scribe_format"]``, so a place whose local file
  is gone can be downloaded again from Documents in My Scribe Account;
* its Location carries the heading it points at (``heading_path``), the
  structural layer of the universal location model (PRD 10.1);
* ``capture_source`` is ``"scribe"``.

They are written straight to the store, as Beacon's own command line does
(the database is WAL, so a running Beacon is not disturbed and picks the new
place up on its next refresh, silently). QUILL's Next Steps write here through
:func:`save_place` (Save a Beacon Place), and Beacon's Tools > Scribe for
Documents > Add Documents in My Scribe Account as Places through :func:`add_library`.

wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import (
    HEALTH_AVAILABLE,
    HEALTH_BROKEN,
    TYPE_DOCUMENT,
    Beacon,
    Resource,
)
from quill.apps.beacon.uld import build_uld

SOURCE = "scribe"
PROVIDER = "scribe"

__all__ = [
    "PROVIDER",
    "SOURCE",
    "add_library",
    "document_id_of",
    "is_scribe",
    "open_store",
    "save_place",
    "scribe_places",
]


def open_store() -> BeaconStore:
    """Beacon's own store, in Beacon's own data folder."""
    from quill.apps.beacon import paths

    return BeaconStore(paths.data_dir() / "beacons.db")


def _canonical(document_id: str) -> str:
    return f"scribe:{document_id}"


def is_scribe(resource: Resource | None) -> bool:
    return bool(resource is not None and resource.provider_ids.get(PROVIDER))


def document_id_of(resource: Resource | None) -> str:
    return resource.provider_ids.get(PROVIDER, "") if resource is not None else ""


def _resource(
    store: BeaconStore, *, document_id: str, title: str, path: Path | None, format_id: str
) -> Resource:
    """The document's Resource, made once and kept up to date with the file."""
    found = store.find_resource_by_canonical(_canonical(document_id))
    resource = found or Resource(type=TYPE_DOCUMENT, canonical_id=_canonical(document_id))
    resource.title = title or resource.title
    resource.provider_ids = {**resource.provider_ids, PROVIDER: document_id}
    if path is not None:
        resource.primary_uri = str(path)
        resource.metadata = {**resource.metadata, "scribe_format": format_id}
    exists = bool(resource.primary_uri) and Path(resource.primary_uri).exists()
    resource.availability = HEALTH_AVAILABLE if exists else HEALTH_BROKEN
    return resource


def save_place(
    store: BeaconStore,
    *,
    document_id: str,
    title: str,
    path: Path,
    format_id: str,
    heading_path: list[str] | None = None,
) -> Beacon:
    """Save a place in a Scribe result, at a heading or at its start."""
    resource = _resource(
        store, document_id=document_id, title=title, path=path, format_id=format_id
    )
    heading = list(heading_path or [])
    beacon = Beacon(
        resource_id=resource.resource_id,
        title=f"{title}, {heading[-1]}" if heading else title,
        capture_source=SOURCE,
        in_inbox=False,
    )
    beacon.locations = [
        build_uld(
            resource_id=resource.resource_id,
            location_type="structural" if heading else "native",
            structural={"heading_path": heading} if heading else None,
            native={"path": str(path), "format": format_id},
            heading_path=heading,
            display_summary=heading[-1] if heading else "The start of the document",
        )
    ]
    return store.put_beacon(beacon, resource=resource)


def scribe_places(store: BeaconStore) -> list[Beacon]:
    """Every place that points into a Scribe result, newest first."""
    places: list[Beacon] = []
    for beacon in store.list_beacons(limit=5000):
        resource = store.get_resource(beacon.resource_id) if beacon.resource_id else None
        if is_scribe(resource):
            places.append(beacon)
    return places


def add_library(
    store: BeaconStore,
    documents: Iterable[tuple[str, str]],
    files: dict[str, tuple[str, Path]],
) -> tuple[int, int]:
    """A place for each Scribe document not already a place: ``(added, already)``.

    *documents* is ``(document id, title)``; *files* is what the Scribe library
    has downloaded of each, ``id -> (format, path)``. A document never
    downloaded is a place with no file yet, which Beacon offers to download.
    """
    known = {
        document_id_of(store.get_resource(b.resource_id))
        for b in store.list_beacons(include_trashed=True, limit=5000)
        if b.resource_id
    }
    added = already = 0
    for document_id, title in documents:
        if not document_id:
            continue
        if document_id in known:
            already += 1
            continue
        format_id, path = files.get(document_id, ("", None))  # type: ignore[assignment]
        resource = _resource(
            store, document_id=document_id, title=title, path=path, format_id=format_id
        )
        beacon = Beacon(
            resource_id=resource.resource_id, title=title, capture_source=SOURCE, in_inbox=False
        )
        beacon.health = resource.availability
        store.put_beacon(beacon, resource=resource)
        known.add(document_id)
        added += 1
    return added, already
