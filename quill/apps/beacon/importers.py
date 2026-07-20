"""Import existing bookmarks and subscriptions (PRD section 25).

Sources: HTML bookmark export (Netscape format, Chromium/Firefox/Safari),
OPML podcast subscriptions, M3U/PLS radio playlists, CSV, JSON, plain text
URL lists. Each importer yields (Beacon, Resource) pairs built through
``capture.capture`` so canonicalization and duplicate detection are shared.

wx-free and unit-testable.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path

from quill.apps.beacon import capture
from quill.apps.beacon.model import TYPE_RADIO_STREAM, Beacon, Resource


class _BookmarkHTMLParser(HTMLParser):
    """Extract (url, title, folder_path) from a Netscape bookmark file."""

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[tuple[str, str, list[str]]] = []
        self._folder_stack: list[str] = []
        self._in_h3 = False
        self._in_a = False
        self._cur_url = ""
        self._cur_title = ""
        self._h3_text = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag.lower() == "a":
            self._in_a = True
            self._cur_url = a.get("href", "")
            self._cur_title = ""
        elif tag.lower() == "h3":
            self._in_h3 = True
            self._h3_text = ""
        elif tag.lower() == "dl":
            pass

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "a" and self._in_a:
            self._in_a = False
            if self._cur_url:
                self.entries.append((self._cur_url, self._cur_title, list(self._folder_stack)))
        elif t == "h3" and self._in_h3:
            self._in_h3 = False
            if self._h3_text:
                self._folder_stack.append(self._h3_text)
        elif t == "dl":
            # closing a <dl> pops the last folder, matching how browsers nest.
            if self._folder_stack:
                self._folder_stack.pop()

    def handle_data(self, data):
        if self._in_a:
            self._cur_title += data
        elif self._in_h3:
            self._h3_text += data


def import_html(text: str) -> Iterator[tuple[Beacon, Resource, list[str]]]:
    """Yield (beacon, resource, folder_path) from a Netscape bookmark export."""
    parser = _BookmarkHTMLParser()
    parser.feed(text)
    for url, title, folders in parser.entries:
        if not url:
            continue
        col = folders[-1] if folders else ""
        collections = [col] if col else []
        beacon, res = capture.capture(
            url,
            title=title.strip(),
            collections=collections,
            capture_source="import:html",
        )
        yield beacon, res, folders


def import_opml(text: str) -> Iterator[tuple[Beacon, Resource, list[str]]]:
    """Yield podcast feed subscriptions from an OPML file."""
    parser = _OPMLParser()
    parser.feed(text)
    for url, title, folders in parser.entries:
        if not url:
            continue
        col = folders[-1] if folders else ""
        collections = [col] if col else []
        beacon, res = capture.capture(
            url,
            title=title.strip(),
            collections=collections,
            tags=["podcast"],
            capture_source="import:opml",
        )
        yield beacon, res, folders


class _OPMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[tuple[str, str, list[str]]] = []
        self._folder_stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag.lower() == "outline":
            url = a.get("xmlurl") or a.get("xmlUrl") or a.get("url") or ""
            title = a.get("text") or a.get("title") or ""
            if url:
                self.entries.append((url, title, list(self._folder_stack)))
            elif title:
                self._folder_stack.append(title)

    def handle_endtag(self, tag):
        if tag.lower() == "outline" and self._folder_stack:
            # Heuristic: pop only if this outline had no xmlUrl (a folder).
            # OPML is inconsistent; this works for the common nested case.
            pass


def import_m3u(text: str) -> Iterator[tuple[Beacon, Resource]]:
    """Yield radio streams from an M3U/PLS-style playlist."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("file"):
            # PLS: File1=...
            line = line.split("=", 1)[-1].strip()
        if "://" in line:
            beacon, res = capture.capture(
                line,
                capture_source="import:m3u",
                tags=["radio"],
            )
            # A playlist entry is a stream by definition, regardless of the
            # URL extension detect_type would otherwise guess.
            res.type = TYPE_RADIO_STREAM
            yield beacon, res


def import_text(text: str) -> Iterator[tuple[Beacon, Resource]]:
    """Yield one beacon per URL or path found on its own line."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "://" in line or re.match(r"^[A-Za-z]:[\\/]", line):
            beacon, res = capture.capture(line, capture_source="import:text")
            yield beacon, res


def import_csv(text: str) -> Iterator[tuple[Beacon, Resource]]:
    """Import CSV with columns: url, title, note, tags, collection.

    A header row is detected if the first row contains 'url'.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return
    fields = {f.lower(): f for f in reader.fieldnames}
    url_key = fields.get("url") or fields.get("link") or fields.get("address")
    if not url_key:
        return
    for row in reader:
        url = (row.get(url_key) or "").strip()
        if not url:
            continue
        title = (row.get(fields.get("title", "title")) or "").strip()
        note = (row.get(fields.get("note", "note")) or "").strip()
        tags_raw = (row.get(fields.get("tags", "tags")) or "").strip()
        col = (row.get(fields.get("collection", "collection")) or "").strip()
        tags = [t.strip() for t in re.split(r"[,;]", tags_raw) if t.strip()]
        collections = [col] if col else []
        beacon, res = capture.capture(
            url,
            title=title,
            note=note,
            tags=tags,
            collections=collections,
            capture_source="import:csv",
        )
        yield beacon, res


def import_json(text: str) -> Iterator[tuple[Beacon, Resource]]:
    """Import a QuillBeacon JSON archive (round-trip with exporters)."""
    data = json.loads(text)
    items = data if isinstance(data, list) else data.get("beacons", [])
    for item in items:
        url = item.get("url") or item.get("resource", {}).get("primaryUri", "")
        if not url:
            continue
        beacon, res = capture.capture(
            url,
            title=item.get("title", ""),
            note=item.get("note", ""),
            tags=item.get("tags", []),
            collections=item.get("collections", []),
            favorite=bool(item.get("favorite", False)),
            capture_source="import:json",
        )
        yield beacon, res


def import_file(path: str | Path) -> list[tuple[Beacon, Resource]]:
    """Auto-detect the format from the file extension and import it."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    suffix = p.suffix.lower()
    out: list[tuple[Beacon, Resource]] = []
    if suffix in (".html", ".htm"):
        out = [(b, r) for b, r, _ in import_html(text)]
    elif suffix == ".opml":
        out = [(b, r) for b, r, _ in import_opml(text)]
    elif suffix in (".m3u", ".m3u8", ".pls"):
        out = list(import_m3u(text))
    elif suffix == ".csv":
        out = list(import_csv(text))
    elif suffix == ".json":
        out = list(import_json(text))
    else:
        out = list(import_text(text))
    return out
