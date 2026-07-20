"""Headless CLI for QuillBeacon (plan section 5): capture, search, export.

A wx-free command line that reads/writes the same on-disk store the desktop app
uses. It is the automation surface -- piping a URL in from a script, searching
headless, and exporting -- so Beacon is useful without a GUI. The magic-link
``verify`` subcommand lives in ``quill.apps.beacon.sync_ui``.

Subcommands::

    python -m quill.apps.beacon.cli capture <url> [--title --note --tags --collection]
    python -m quill.apps.beacon.cli search <terms> [--collection --tag --type --sort]
    python -m quill.apps.beacon.cli export <format> [--path --collection]

Fail-safe: every subcommand returns a non-zero exit code and a message on
failure; it never raises out of the top level.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from quill.apps.beacon import capture, exporters, routing
from quill.apps.beacon import search as searchmod
from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.paths import data_dir

EXPORT_FORMATS = ("json", "html", "markdown", "csv", "opml", "m3u", "text")


def _open_store() -> BeaconStore:
    return BeaconStore(data_dir() / "beacons.db")


def _read_url_arg(value: str | None) -> str:
    """Resolve the capture target: an explicit arg, or stdin (first URL/path)."""
    if value and value != "-":
        return value
    text = sys.stdin.read()
    return _first_url_or_line(text)


def _first_url_or_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


# -- capture -----------------------------------------------------------------


def cmd_capture(args) -> int:
    url = _read_url_arg(args.url)
    if not url:
        print("capture: no URL or path provided", file=sys.stderr)
        return 2
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    collections = [args.collection] if args.collection else []
    beacon, res = capture.capture(
        url,
        title=args.title or "",
        note=args.note or "",
        tags=tags,
        collections=collections,
        favorite=args.favorite,
        inbox=args.inbox,
        media_start_ms=args.media_start,
        capture_source="cli",
    )
    if args.type:
        res.type = args.type
    routing.route(beacon, res, routing.load_rules(data_dir()))
    store = _open_store()
    try:
        store.put_beacon(beacon, resource=res)
        print(f"captured: {beacon.title} ({beacon.beacon_id})")
        return 0
    except Exception as exc:  # fail-safe
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()


# -- search ------------------------------------------------------------------


def _beacon_summary(store: BeaconStore, b) -> dict[str, Any]:
    res = store.get_resource(b.resource_id) if b.resource_id else None
    return {
        "id": b.beacon_id,
        "title": b.title,
        "url": res.primary_uri if res else "",
        "note": b.note,
        "tags": b.tags,
        "collections": b.collections,
        "type": res.type if res else "",
        "favorite": b.favorite,
    }


def cmd_search(args) -> int:
    terms = " ".join(args.query or [])
    query = terms
    for t in args.tag or []:
        query += f" tag:{t}"
    for t in args.type or []:
        query += f" type:{t}"
    if args.favorite:
        query += " favorite"
    if args.inbox:
        query += " inbox"
    if args.has_note:
        query += " has:note"
    store = _open_store()
    try:
        results = searchmod.search(
            store,
            query,
            scope_collection=args.collection,
            sort=args.sort,
            limit=args.limit,
        )
    except Exception as exc:
        print(f"search failed: {exc}", file=sys.stderr)
        store.close()
        return 1
    if args.json:
        print(
            json.dumps([_beacon_summary(store, b) for b in results], ensure_ascii=False, indent=2)
        )
    else:
        if not results:
            print("No matches.")
        for b in results:
            res = store.get_resource(b.resource_id) if b.resource_id else None
            url = res.primary_uri if res else ""
            print(b.title or "(untitled)")
            if url:
                print(f"  {url}")
            if b.note:
                preview = b.note.replace("\n", " ")[:100]
                print(f"  note: {preview}")
            if b.tags:
                print(f"  tags: {', '.join(b.tags)}")
    store.close()
    return 0


# -- export ------------------------------------------------------------------


def cmd_export(args) -> int:
    fmt = args.format
    fn = getattr(exporters, f"export_{fmt}", None)
    if fn is None:
        print(f"export: unknown format {fmt}", file=sys.stderr)
        return 2
    store = _open_store()
    try:
        if args.collection:
            beacons = searchmod.search(
                store,
                "",
                scope_collection=args.collection,
                sort=searchmod.SORT_ADDED,
                limit=args.limit or 100000,
            )
        else:
            beacons = None  # exporter uses the whole library
        text = fn(store, beacons)
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        store.close()
        return 1
    store.close()
    if args.path:
        Path(args.path).write_text(text, encoding="utf-8")
        print(f"wrote {args.path}")
    else:
        sys.stdout.write(text)
    return 0


# -- dispatch ----------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="quill.apps.beacon.cli", description="QuillBeacon headless CLI"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="Capture a URL or path into the library")
    c.add_argument("url", nargs="?", default="-", help="URL or path; '-' or omitted reads stdin")
    c.add_argument("--title", default="")
    c.add_argument("--note", default="")
    c.add_argument("--tags", default="", help="Comma-separated tags")
    c.add_argument("--collection", default="")
    c.add_argument("--type", default="", help="Override resource type")
    c.add_argument("--favorite", action="store_true")
    c.add_argument("--inbox", dest="inbox", action="store_true", default=True)
    c.add_argument("--no-inbox", dest="inbox", action="store_false")
    c.add_argument("--media-start", type=int, default=0, help="Media start time in milliseconds")
    c.set_defaults(func=cmd_capture)

    s = sub.add_parser("search", help="Search the library and print matches")
    s.add_argument("query", nargs="*", help="Search terms")
    s.add_argument("--collection", default="")
    s.add_argument("--tag", action="append", default=[])
    s.add_argument("--type", action="append", default=[])
    s.add_argument("--sort", default=searchmod.SORT_ADDED)
    s.add_argument("--limit", type=int, default=100)
    s.add_argument("--favorite", action="store_true")
    s.add_argument("--inbox", action="store_true")
    s.add_argument("--has-note", action="store_true")
    s.add_argument("--json", action="store_true", help="Output JSON")
    s.set_defaults(func=cmd_search)

    e = sub.add_parser("export", help="Export the library (or one collection)")
    e.add_argument("format", choices=EXPORT_FORMATS)
    e.add_argument("--path", default="", help="Write to file (default stdout)")
    e.add_argument("--collection", default="")
    e.add_argument("--limit", type=int, default=0)
    e.set_defaults(func=cmd_export)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:
        return 0
    except Exception as exc:  # last-resort fail-safe
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
