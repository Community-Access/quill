"""Read-only web publish surface (PRD 27.1; PLAN-beacon-surfaces section 12).

Render a user's explicitly-published collection as a self-contained, accessible
HTML page, and manage the on-disk ``published/`` folder plus a publish token that
gates the localhost preview served by the capture bridge.

Design constraints (plan doc section 12):
- Read only. There is no write path back into the library.
- No auth beyond the publish token. The token travels in the preview URL path so
  the link is shareable; the bridge binds 127.0.0.1, so the preview is local-only.
- Fail-safe. Every method returns a dict and never raises; filesystem errors turn
  into ``{"error": ...}`` replies. Nothing the web can do can modify the library.
- Reversible. Unpublish removes only the generated files; it never touches the
  database or sync state, and it never mutates ``Collection.sharing``.

wx-free and unit-testable.
"""

from __future__ import annotations

import html
import json
import re
import secrets
import shutil
import time
from pathlib import Path

from quill.apps.beacon import search as searchmod
from quill.apps.beacon.model import Beacon, Collection

PUBLISH_DIR = "published"
INDEX_NAME = "index.html"
MANIFEST_NAME = "manifest.json"
_TOKEN_LEN = 16  # bytes -> ~22 urlsafe chars

# Slug character set: lowercase letters, digits, hyphen. Anything else collapses.
_SLUG_RE = re.compile(r"[^a-z0-9]+")
# Path separators and traversal sequences are rejected outright so a collection
# name can never escape the ``published/`` folder.
_FORBIDDEN = re.compile(r"[\\/]|(\.\.)")


def slugify(name: str) -> str | None:
    """Return a filesystem-safe slug for ``name``, or None if it is unsafe.

    Returns None when the name contains path separators or ``..`` (so callers
    fail closed instead of writing outside ``published/``), or when the name
    slugs to empty (nothing safe to use as a directory name).
    """
    if name is None:
        return None
    if _FORBIDDEN.search(name):
        return None
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not slug:
        return None
    return slug


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _note_to_html(note: str) -> str:
    """Render a free-text note as paragraph HTML, preserving line breaks."""
    if not note:
        return ""
    # Build paragraphs split on blank lines; single newlines become <br>.
    blocks: list[str] = []
    para: list[str] = []
    for line in note.splitlines():
        if line.strip() == "":
            if para:
                blocks.append("<br>".join(para))
                para = []
        else:
            para.append(_esc(line))
    if para:
        blocks.append("<br>".join(para))
    return "\n".join(f"      <p>{block}</p>" for block in blocks)


_CSS = """
:root { color-scheme: light dark; }
body { font: 100%/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
  "Helvetica Neue", Arial, sans-serif; max-width: 46rem; margin: 1.5rem auto;
  padding: 0 1rem; color: CanvasText; background: Canvas; }
.skip { position: absolute; left: -9999px; top: auto; width: 1px; height: 1px;
  overflow: hidden; }
.skip:focus { position: static; width: auto; height: auto; overflow: visible;
  padding: .5rem 1rem; background: Highlight; color: HighlightText; }
header, footer { border-top: 1px solid; padding-top: .5rem; margin-top: 1.5rem;
  color: GrayText; }
main h1 { margin-bottom: 0; }
.meta { color: GrayText; font-size: .9rem; margin: .25rem 0 1.5rem; }
article { margin: 1.5rem 0; padding: .25rem 0; border-top: 1px solid; }
article:first-of-type { border-top: none; }
h2 { margin: .5rem 0; }
.tags { list-style: none; padding: 0; margin: .25rem 0; font-size: .85rem; }
.tags li { display: inline; margin-right: .5rem; color: GrayText; }
.tags li::before { content: "#"; }
a { color: LinkText; }
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; scroll-behavior:
    auto !important; }
}
""".strip()


def render_collection_html(
    store,
    collection: Collection,
    beacons: list[Beacon],
    *,
    published_at: int = 0,
) -> str:
    """Render a self-contained, accessible HTML5 page for a collection.

    ``store`` is a :class:`quill.apps.beacon.db.BeaconStore` used only to resolve each
    beacon's resource (for the link URI and link text). All interpolated text is
    HTML-escaped. No JavaScript is emitted.
    """
    name = _esc(collection.name or "Untitled collection")
    desc = _esc(collection.description or "")
    count = len(beacons)
    date_line = f"Published {published_at}" if published_at else ""
    meta = " · ".join(p for p in (date_line, f"{count} item{'s' if count != 1 else ''}") if p)

    articles: list[str] = []
    for b in beacons:
        res = store.get_resource(b.resource_id) if b.resource_id else None
        uri = res.primary_uri if res else ""
        res_title = (res.title if res else "") or b.title or "Untitled"
        title = _esc(b.title or res_title or "Untitled")
        parts = ["    <article>", f"      <h2>{title}</h2>"]
        note_html = _note_to_html(b.note)
        if note_html:
            parts.append(note_html)
        if b.tags:
            tag_items = "".join(f"<li>{_esc(t)}</li>" for t in b.tags)
            parts.append(f'      <ul class="tags" aria-label="Tags">{tag_items}</ul>')
        if uri:
            # Link text is the resource title, never the bare URL; rel=noopener
            # for untrusted destinations. href is escaped (quote=True) too.
            parts.append(
                f'      <p><a href="{_esc(uri)}" rel="noopener noreferrer">'
                f"{_esc(res_title)}</a></p>"
            )
        else:
            # No resolvable location: show the resource title as plain text so
            # the title is conveyed without an empty/dead link.
            parts.append(f"      <p>{_esc(res_title)}</p>")
        parts.append("    </article>")
        articles.append("\n".join(parts))

    out = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>{name}</title>",
        f"  <style>\n{_CSS}\n  </style>",
        "</head>",
        "<body>",
        '  <a class="skip" href="#main">Skip to content</a>',
        '  <main id="main" aria-labelledby="collection-title">',
        f'    <h1 id="collection-title">{name}</h1>',
    ]
    if desc:
        out.append(f"    <p>{desc}</p>")
    if meta:
        out.append(f'    <p class="meta">{_esc(meta)}</p>')
    out.extend(articles)
    out.append(
        "    <footer>\n"
        "      <p>Read-only view published by QuillBeacon. "
        "Nothing on this page can modify the library.</p>\n"
        "    </footer>"
    )
    out.append("  </main>")
    out.append("</body>")
    out.append("</html>")
    return "\n".join(out) + "\n"


def render_index_html(published: list[dict]) -> str:
    """Render the top-level index listing all published collections."""
    rows = []
    for item in published:
        slug = _esc(item.get("slug", ""))
        name = _esc(item.get("name", "Untitled"))
        count = item.get("count", 0)
        rows.append(
            f'  <li><a href="{slug}/">{name}</a> '
            f'<span class="meta">({count} item{"s" if count != 1 else ""})</span></li>'
        )
    list_html = "\n".join(rows) if rows else "  <li>No published collections.</li>"
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>QuillBeacon published collections</title>\n"
        f"  <style>\n{_CSS}\n  </style>\n</head>\n<body>\n"
        '  <a class="skip" href="#main">Skip to content</a>\n'
        '  <main id="main" aria-labelledby="h">\n'
        '    <h1 id="h">Published collections</h1>\n'
        f"    <ul>\n{list_html}\n    </ul>\n"
        "    <footer><p>Read-only views published by QuillBeacon.</p></footer>\n"
        "  </main>\n</body>\n</html>\n"
    )


class PublishManager:
    """Owns the ``published/`` folder under the data dir.

    The manager is fail-safe: every public method returns a JSON-able dict and
    never raises. It holds no store connection of its own; it borrows the caller's
    store for reads during ``publish``.
    """

    def __init__(self, store, data_dir) -> None:
        self.store = store
        self.data_dir = Path(data_dir)
        self.root = self.data_dir / PUBLISH_DIR

    # -- paths ----------------------------------------------------------------

    def _dir_for(self, slug: str) -> Path:
        return self.root / slug

    def _manifest_path(self, slug: str) -> Path:
        return self._dir_for(slug) / MANIFEST_NAME

    def _html_path(self, slug: str) -> Path:
        return self._dir_for(slug) / INDEX_NAME

    # -- public API -----------------------------------------------------------

    def publish(self, collection_name: str, *, port: int | None = None) -> dict:
        """Publish ``collection_name`` as a static HTML page.

        Returns ``{ok, slug, token, path, preview_url, count}`` on success, or
        ``{error}`` on failure. Re-publishing a collection rotates its token and
        refreshes the rendered page.
        """
        slug = slugify(collection_name)
        if slug is None:
            return {"error": "unsafe collection name"}
        col = self.store.collection_by_name(collection_name)
        if col is None:
            return {"error": "collection not found"}
        try:
            beacons = searchmod.search(
                self.store,
                "",
                scope_collection=collection_name,
                sort=searchmod.SORT_ADDED,
                limit=100000,
            )
        except Exception as exc:  # fail-safe: never raise out of publish
            return {"error": f"query failed: {exc}"}

        token = secrets.token_urlsafe(_TOKEN_LEN)
        published_at = int(time.time())
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            page = render_collection_html(self.store, col, beacons, published_at=published_at)
            d = self._dir_for(slug)
            d.mkdir(parents=True, exist_ok=True)
            self._html_path(slug).write_text(page, encoding="utf-8")
            manifest = {
                "collection_id": col.collection_id,
                "name": col.name,
                "slug": slug,
                "token": token,
                "published_at": published_at,
                "count": len(beacons),
            }
            self._manifest_path(slug).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            self._write_top_index()
        except OSError as exc:
            return {"error": f"write failed: {exc}"}

        preview = ""
        if port:
            preview = f"http://127.0.0.1:{port}/published/{token}/"
        return {
            "ok": True,
            "slug": slug,
            "token": token,
            "path": str(self._html_path(slug)),
            "preview_url": preview,
            "count": len(beacons),
        }

    def unpublish(self, collection_name: str) -> dict:
        """Remove the published page for ``collection_name``. Reversible."""
        slug = slugify(collection_name)
        if slug is None:
            return {"error": "unsafe collection name"}
        d = self._dir_for(slug)
        try:
            if not d.exists():
                return {"error": "not published"}
            shutil.rmtree(d)
            self._write_top_index()
        except OSError as exc:
            return {"error": f"remove failed: {exc}"}
        return {"ok": True, "slug": slug}

    def list_published(self) -> list[dict]:
        """Return manifest dicts for every published collection."""
        out: list[dict] = []
        if not self.root.exists():
            return out
        try:
            for entry in self.root.iterdir():
                if not entry.is_dir():
                    continue
                mpath = entry / MANIFEST_NAME
                if not mpath.exists():
                    continue
                try:
                    out.append(json.loads(mpath.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    continue
        except OSError:
            return out
        return out

    def get_by_token(self, token: str) -> dict | None:
        """Return ``{slug, html_path, manifest}`` for a publish token, or None."""
        if not token:
            return None
        for item in self.list_published():
            t = item.get("token", "")
            if t and secrets.compare_digest(str(t), str(token)):
                slug = item.get("slug", "")
                return {"slug": slug, "html_path": str(self._html_path(slug)), "manifest": item}
        return None

    def is_published(self, collection_name: str) -> bool:
        slug = slugify(collection_name)
        return bool(slug and self._dir_for(slug).exists())

    # -- internals -----------------------------------------------------------

    def _write_top_index(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            (self.root / INDEX_NAME).write_text(
                render_index_html(self.list_published()), encoding="utf-8"
            )
        except OSError:
            pass
