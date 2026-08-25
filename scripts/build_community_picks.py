"""Build the Community Picks catalogue from the curated source + approved issues.

One input path into the catalogue, whatever route an entry took to get there:
``docs/picks-source.json`` for bulk curation, and every issue labelled
``pick:approved`` for the ones suggested from inside Radio, from the website,
or added by a maintainer on the review page. Both carry the same
machine-readable block, parsed by ``core.pick_suggestion.parse_issue_body``.

Writes two files from one document, so the shipped copy and the served copy can
never disagree:

* ``docs/site/picks/v1/picks.json`` -- served from GitHub Pages, which the
  existing pages workflow deploys because ``docs/**`` changed.
* ``quill/core/data/community_picks.json`` -- the copy bundled in the app, so
  the picker works offline and on first run.

Run by ``.github/workflows/picks-build.yml``; runnable by hand with
``--issues-json`` (or with neither, to rebuild from the source alone).

Usage::

    python scripts/build_community_picks.py --check      # validate, write nothing
    python scripts/build_community_picks.py --issues-json approved.json
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
SOURCE = _ROOT / "docs" / "picks-source.json"
SITE = _ROOT / "docs" / "site" / "picks" / "v1" / "picks.json"
BUNDLED = _ROOT / "quill" / "core" / "data" / "community_picks.json"
SCHEMA = _ROOT / "quill" / "core" / "schemas" / "community_picks.json"

DEFAULT_COLLECTION_ID = "community"
DEFAULT_COLLECTION_TITLE = "Community suggestions"


def slug(text: str) -> str:
    """A stable, URL-safe id.

    ASCII-folded first: ``str.isalnum()`` is true for "n with tilde", so a
    naive slug of "Podcasts en Español de la ACB" keeps a character that the id
    pattern -- and anything that puts an id in a URL -- will not accept. Caught
    by the schema the first time this ran.
    """
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    out = "".join(c.lower() if c.isascii() and c.isalnum() else "-" for c in folded)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")[:64].strip("-")


def _item_from_issue(issue: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """``(collection title, item)`` from one approved issue, or None to skip."""
    sys.path.insert(0, str(_ROOT))
    from quill.core.pick_suggestion import parse_issue_body

    payload = parse_issue_body(str(issue.get("body") or ""))
    if not payload:
        return None
    title = (payload.get("title") or "").strip()
    url = (payload.get("feed_url") or payload.get("stream_url") or "").strip()
    kind = (payload.get("type") or "").strip()
    if not title or not url or kind not in ("stream", "podcast"):
        return None
    # http allowed: see the "url" definition in the schema for why refusing it
    # would exclude 41% of the stations Radio can already play.
    if not url.lower().startswith(("https://", "http://")):
        return None

    item: dict[str, Any] = {
        "id": slug(title),
        "type": kind,
        "title": title,
        # The day it was approved, so the picker can say "new since you last
        # looked". Taken from the issue rather than from now(), so a rebuild
        # does not make every entry look new again.
        "added": str(issue.get("closed_at") or issue.get("updated_at") or "")[:10],
    }
    for key in ("description", "language", "homepage"):
        value = (payload.get(key) or "").strip()
        if value:
            item[key] = value
    item["feed_url" if kind == "podcast" else "stream_url"] = url
    if not item["added"]:
        item.pop("added")
    return (payload.get("collection") or "").strip(), item


def build(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """The catalogue, from the curated source plus *issues*."""
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    collections: list[dict[str, Any]] = [
        {key: value for key, value in collection.items()}
        for collection in source.get("collections", [])
    ]
    by_title = {collection["title"]: collection for collection in collections}
    seen = {
        (item.get("feed_url") or item.get("stream_url") or item.get("node_id") or "").lower()
        for collection in collections
        for item in collection["items"]
    }
    seen_ids = {item["id"] for collection in collections for item in collection["items"]}

    for issue in issues:
        parsed = _item_from_issue(issue)
        if parsed is None:
            print(f"  skipped #{issue.get('number')}: no readable pick block")
            continue
        wanted, item = parsed
        target = (item.get("feed_url") or item.get("stream_url") or "").lower()
        if target in seen:
            print(f"  skipped #{issue.get('number')}: {item['title']} is already listed")
            continue
        # ids are identity; a clash would make two picks look like one.
        base, n = item["id"], 2
        while item["id"] in seen_ids:
            item["id"] = f"{base}-{n}"
            n += 1
        seen.add(target)
        seen_ids.add(item["id"])

        title = wanted or DEFAULT_COLLECTION_TITLE
        collection = by_title.get(title)
        if collection is None:
            collection = {
                "id": slug(title) or DEFAULT_COLLECTION_ID,
                "title": title,
                "description": "Suggested by the community and approved.",
                "items": [],
            }
            collections.append(collection)
            by_title[title] = collection
        collection["items"].append(item)
        print(f"  added #{issue.get('number')}: {item['title']} -> {title}")

    return {
        "format": "quillville-picks",
        "version": 1,
        "updated": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "title": "QuillVille Community Picks",
        "description": "Stations, podcasts and places the community recommends.",
        "collections": collections,
    }


def validate(document: dict[str, Any]) -> None:
    """Refuse to publish anything the schema does not accept."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - CI installs it
        print("jsonschema not installed; skipping schema validation", file=sys.stderr)
        return
    jsonschema.validate(document, json.loads(SCHEMA.read_text(encoding="utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issues-json", type=Path, help="approved issues, as the GitHub API returns them"
    )
    parser.add_argument("--check", action="store_true", help="validate and write nothing")
    args = parser.parse_args()

    issues: list[dict[str, Any]] = []
    if args.issues_json and args.issues_json.is_file():
        issues = json.loads(args.issues_json.read_text(encoding="utf-8")) or []
    print(f"building from {SOURCE.name} + {len(issues)} approved issue(s)")

    document = build(issues)
    validate(document)
    total = sum(len(collection["items"]) for collection in document["collections"])
    print(f"{total} picks in {len(document['collections'])} collection(s)")

    if args.check:
        print("--check: nothing written")
        return 0
    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    for target in (SITE, BUNDLED):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
