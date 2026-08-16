"""The instant search lane: local FTS rows for Find Stations.

Kept beside the dialog rather than in it (GATE-11), and guarded end to end:
the catalog never breaks a search -- it only ever adds to one.
"""

from __future__ import annotations

from quill.core.radio.models import RadioStation


def catalog_search_rows(store: object, name: str, *, limit: int) -> list[RadioStation]:
    """Local matches for *name*, already shaped for the results list."""
    if store is None or not name:
        return []
    try:
        from quill.core.radio.catalog.read import _SOURCE_LABELS

        return [
            row.to_station(source_label=_SOURCE_LABELS.get(row.source_id, row.source_id))
            for row in store.search(name, limit=limit)  # type: ignore[attr-defined]
        ]
    except Exception:  # noqa: BLE001 - the catalog never breaks a search
        return []
