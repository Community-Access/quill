"""Read Site as Document (PRD 15.5; W7): a site, a menu or a category as one document.

:func:`document_pages` gathers what is read, in reading order:

- **the whole site:** its published pages in page order (menu order, then
  each page's children under it);
- **a menu:** the pages and posts its links point at, in the menu's own order
  and nesting; a plain link to an outside address is named, not read;
- **a category:** its published posts, oldest first, as a book reads.

Only published content is read: drafts, private and password-protected pages
are left out, and the document says how many. Loading is bounded
(:data:`LIMIT` items); a site with more is named as cut short.

:func:`site_document` writes the Markdown the editor opens, ready for its
Word, EPUB and DAISY exports: a heading per page, the page's own headings
nested beneath it, lists, links and picture descriptions kept (through
:func:`quill.core.html_to_markdown.html_to_markdown`), and at the top where
it was read from, what was read and when, so an archive says what it is.

Wx-free; the Workbench runs it off the UI thread.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.html_to_markdown import html_to_markdown
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import kind_route, raw_text, rendered
from quill.core.wordpress.workbench_rows import item_row, tree_order

__all__ = ["LIMIT", "ReadScope", "document_pages", "site_document"]

LIMIT = 500
_FIELDS = "id,title,content,link,modified,parent,menu_order,status,type"


@dataclass(frozen=True)
class ReadScope:
    """What to read: ``site``, ``menu`` (with its id) or ``category`` (with its id)."""

    kind: str = "site"
    ident: int = 0
    name: str = ""

    @property
    def words(self) -> str:
        if self.kind == "menu":
            return f"the pages and posts in the menu {self.name}, in the menu's order"
        if self.kind == "category":
            return f"the published posts in the category {self.name}, oldest first"
        return "every published page, in page order"


def _protected(raw: Mapping[str, Any]) -> bool:
    content = raw.get("content")
    return isinstance(content, dict) and bool(content.get("protected"))


def document_pages(
    api: WordPressApi, scope: ReadScope, *, site: str = "", limit: int = LIMIT
) -> tuple[list[Mapping[str, Any]], list[str]]:
    """The items to read, in order, and the notes the document must carry."""
    notes: list[str] = []
    if scope.kind == "menu":
        found, more = _menu_pages(api, scope.ident, limit, notes)
    else:
        query: dict[str, object] = {"status": "publish", "_fields": _FIELDS}
        if scope.kind == "category":
            route = "wp/v2/posts"
            query.update({"categories": scope.ident, "orderby": "date", "order": "asc"})
        else:
            route = "wp/v2/pages"
            query.update({"orderby": "menu_order", "order": "asc"})
        found = []
        more = False
        for raw in api.iter_collection(route, query, per_page=100, max_pages=limit // 100 + 1):
            if len(found) >= limit:
                more = True
                break
            found.append(raw)
        if scope.kind == "site":
            ordered = tree_order([item_row(r, "page", site) for r in found])
            found = [r.raw for r in ordered]
    hidden = [r for r in found if _protected(r)]
    if hidden:
        notes.append(f"{len(hidden)} password-protected pages are left out.")
    found = [r for r in found if not _protected(r)]
    notes.insert(0, "Only published content is read; drafts and private pages are left out.")
    if more:
        notes.append(f"Only the first {limit} are read; the site has more.")
    return found, notes


def _menu_pages(
    api: WordPressApi, menu_id: int, limit: int, notes: list[str]
) -> tuple[list[Mapping[str, Any]], bool]:
    items = list(
        api.iter_collection("wp/v2/menu-items", {"menus": menu_id, "context": "edit"}, per_page=100)
    )
    rows = [item_row({**i, "parent": int(i.get("parent", 0) or 0)}, "menu", "") for i in items]
    ordered = [r.raw for r in tree_order(sorted(rows, key=lambda r: _order(r.raw)))]
    found: list[Mapping[str, Any]] = []
    skipped: list[str] = []
    for item in ordered:
        if len(found) >= limit:
            return found, True
        kind = str(item.get("object", "") or "")
        ident = int(item.get("object_id", 0) or 0)
        if item.get("type") != "post_type" or not ident:
            skipped.append(raw_text(item.get("title")) or str(item.get("url", "")))
            continue
        try:
            raw = api.get(f"{kind_route(kind)}/{ident}", _fields=_FIELDS)
        except WordPressApiError:
            skipped.append(raw_text(item.get("title")) or f"{kind} {ident}")
            continue
        if isinstance(raw, dict) and raw.get("status", "publish") == "publish":
            found.append(raw)
    if skipped:
        notes.append(
            f"Links not read, being outside addresses or not published: {', '.join(skipped)}."
        )
    return found, False


def _order(raw: Mapping[str, Any]) -> int:
    return int(raw.get("menu_order", 0) or 0)


def _demote(markdown: str, by: int = 2) -> str:
    """Each heading *by* levels deeper, so a page's own headings sit under its title."""

    def deeper(match: re.Match[str]) -> str:
        return "#" * min(6, len(match.group(1)) + by) + " "

    return re.sub(r"^(#{1,6}) ", deeper, markdown, flags=re.MULTILINE)


def _body(raw: Mapping[str, Any]) -> str:
    content = raw.get("content")
    html = ""
    if isinstance(content, dict):
        html = str(content.get("rendered") or content.get("raw") or "")
    elif content is not None:
        html = str(content)
    return _demote(html_to_markdown(html)).strip()


def site_document(
    site: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    address: str = "",
    scope: str = "",
    made: str = "",
    notes: Sequence[str] = (),
) -> str:
    """The pages (already in reading order) as one Markdown document."""
    parts = [f"# {site}", ""]
    facts = [
        ("Read from", address),
        ("What was read", scope),
        ("Read on", made),
        ("Pages", str(len(pages)) if scope else ""),
    ]
    listed = [f"- {label}: {value}" for label, value in facts if value]
    listed += [f"- Note: {note}" for note in notes]
    if listed:
        parts.extend([*listed, ""])
    for page in pages:
        title = rendered(page.get("title")) or raw_text(page.get("title")) or "(untitled)"
        parts.append(f"## {title}")
        parts.append("")
        link = str(page.get("link", "") or "")
        changed = str(page.get("modified", "") or "")[:10]
        said = [f"Address: {link}." if link else "", f"Last changed: {changed}." if changed else ""]
        if link or changed:
            parts.extend([" ".join(s for s in said if s), ""])
        parts.append(_body(page))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
