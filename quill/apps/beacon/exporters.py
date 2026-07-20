"""Export the library to open, documented formats (PRD section 26).

JSON archive (the canonical portable format), human-readable HTML bookmarks
(Netscape format, re-importable), Markdown, CSV, OPML for podcast feeds, M3U
for radio streams, and plain text URLs. Every export is a plain string so it
can be written to a file or the clipboard.

wx-free and unit-testable.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable

from quill.apps.beacon import db as dbmod
from quill.apps.beacon.model import (
    SCHEMA_VERSION,
    TYPE_PODCAST_EPISODE,
    TYPE_PODCAST_SHOW,
    TYPE_RADIO_STATION,
    TYPE_RADIO_STREAM,
    Beacon,
)


def _beacons(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None) -> list[Beacon]:
    if beacons is not None:
        return list(beacons)
    return store.list_beacons(include_trashed=False, limit=100000)


def _resource(store: dbmod.BeaconStore, b: Beacon):
    return store.get_resource(b.resource_id) if b.resource_id else None


def export_json(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None = None) -> str:
    """Portable JSON archive (PRD 24.2 example shape)."""
    items = []
    for b in _beacons(store, beacons):
        res = _resource(store, b)
        items.append({
            "schemaVersion": SCHEMA_VERSION,
            "beaconId": b.beacon_id,
            "title": b.title,
            "note": b.note,
            "tags": b.tags,
            "collections": b.collections,
            "favorite": b.favorite,
            "createdAt": b.date_added,
            "resource": {
                "type": res.type if res else "uri",
                "canonicalId": res.canonical_id if res else "",
                "title": res.title if res else "",
                "primaryUri": res.primary_uri if res else "",
            },
            "locations": [loc.to_row() for loc in b.locations],
        })
    return json.dumps({"beacons": items}, indent=2, ensure_ascii=False)


def _html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def export_html(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None = None) -> str:
    """Netscape bookmark HTML, re-importable by ``importers.import_html``."""
    by_col: dict[str, list[Beacon]] = {}
    for b in _beacons(store, beacons):
        cols = b.collections or ["Uncategorized"]
        for c in cols:
            by_col.setdefault(c, []).append(b)
    out = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>QuillBeacon export</TITLE>",
        "<H1>QuillBeacon</H1>",
        "<DL><p>",
    ]
    for col in sorted(by_col):
        out.append(f"    <DT><H3>{_html_escape(col)}</H3>")
        out.append("    <DL><p>")
        for b in by_col[col]:
            res = _resource(store, b)
            url = res.primary_uri if res else ""
            if not url:
                continue
            out.append(f'        <DT><A HREF="{_html_escape(url)}">{_html_escape(b.title)}</A>')
            if b.note:
                out.append(f"        <DD>{_html_escape(b.note)}")
        out.append("    </DL><p>")
    out.append("</DL><p>")
    return "\n".join(out) + "\n"


def export_markdown(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None = None) -> str:
    """Markdown link list grouped by collection."""
    by_col: dict[str, list[Beacon]] = {}
    for b in _beacons(store, beacons):
        col = (b.collections or ["Uncategorized"])[0]
        by_col.setdefault(col, []).append(b)
    lines = ["# QuillBeacon export", ""]
    for col in sorted(by_col):
        lines.append(f"## {col}")
        lines.append("")
        for b in by_col[col]:
            res = _resource(store, b)
            url = res.primary_uri if res else ""
            if not url:
                lines.append(f"- {b.title}")
            else:
                lines.append(f"- [{b.title}]({url})")
            if b.note:
                lines.append(f"  - {b.note}")
        lines.append("")
    return "\n".join(lines)


def export_csv(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None = None) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["url", "title", "note", "tags", "collection", "type", "added"])
    for b in _beacons(store, beacons):
        res = _resource(store, b)
        writer.writerow([
            res.primary_uri if res else "",
            b.title,
            b.note,
            ";".join(b.tags),
            ";".join(b.collections),
            res.type if res else "",
            b.date_added,
        ])
    return buf.getvalue()


def export_opml(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None = None) -> str:
    """OPML for podcast feeds/shows only."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0"><head><title>QuillBeacon podcasts</title></head><body>',
    ]
    for b in _beacons(store, beacons):
        res = _resource(store, b)
        if not res or res.type not in (TYPE_PODCAST_SHOW, TYPE_PODCAST_EPISODE):
            continue
        url = res.primary_uri
        lines.append(
            f'  <outline type="rss" text="{_attr(b.title)}" '
            f'title="{_attr(b.title)}" xmlUrl="{_attr(url)}" />'
        )
    lines.append("</body></opml>")
    return "\n".join(lines)


def export_m3u(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None = None) -> str:
    """M3U playlist of radio streams only."""
    lines = ["#EXTM3U"]
    for b in _beacons(store, beacons):
        res = _resource(store, b)
        if not res or res.type not in (TYPE_RADIO_STATION, TYPE_RADIO_STREAM):
            continue
        lines.append(f"#EXTINF:-1,{b.title}")
        lines.append(res.primary_uri)
    return "\n".join(lines) + "\n"


def export_text(store: dbmod.BeaconStore, beacons: Iterable[Beacon] | None = None) -> str:
    """Plain text, one URL per line."""
    out = []
    for b in _beacons(store, beacons):
        res = _resource(store, b)
        if res and res.primary_uri:
            out.append(res.primary_uri)
    return "\n".join(out) + "\n"


def _attr(s: str) -> str:
    return (s or "").replace('"', "").replace("<", "").replace(">", "").replace("&", "&amp;")
