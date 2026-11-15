"""Export a site as WordPress eXtended RSS 1.2, built on this computer (wp_missing.md, Moving).

WordPress makes a WXR file in wp-admin (Tools > Export); REST has no route
for it. QUILL writes the same format from what it reads over REST, so any
WordPress site's importer (and QUILL's own Import WXR as Drafts) can read it:

- the channel: the site's name, address, description and language;
- authors (``wp:author``): login, email and names where the account may list
  people with ``context=edit``, otherwise their public slug and name;
- categories, tags and every other public taxonomy's terms (``wp:category``,
  ``wp:tag``, ``wp:term``), and menus as ``nav_menu`` terms;
- items: posts, pages, synced patterns and every custom type REST shows, with
  their terms, the REST-visible custom fields (``wp:postmeta``), the featured
  image (``_thumbnail_id``) and comments the account may read; attachments as
  items with their ``wp:attachment_url``; menu items as ``nav_menu_item``.

A **scope** (:class:`Scope`) narrows it to posts, pages, a date range or a
category; then only the authors, terms and files those items use go in, as
WordPress's own exporter does. Items are written as they are read, so a big
site is never held in memory at once, and each type stops at :data:`MAX_ROWS`
with the truncation named. The report (:attr:`ExportReport.left_out`) names
what did not travel and why. :func:`validate_wxr` reads the finished file back
through :mod:`quill.core.safe_xml` and checks its WXR shape.

Wx-free; reads only, through the site's own client, off the UI thread.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any
from xml.sax.saxutils import escape, quoteattr

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered

__all__ = [
    "MAX_ROWS",
    "NS",
    "SCOPES",
    "ExportReport",
    "Scope",
    "export_wxr",
]

MAX_ROWS = 10000
"""At most this many rows of one kind are written; the report names any truncation."""
NS = {
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "wfw": "http://wellformedweb.org/CommentAPI/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "wp": "http://wordpress.org/export/1.2/",
}
SCOPES = ("everything", "posts", "pages", "dates", "category")
_SKIP_TYPES = frozenset({
    "attachment",
    "nav_menu_item",
    "wp_template",
    "wp_template_part",
    "wp_navigation",
    "wp_global_styles",
    "wp_font_family",
    "wp_font_face",
})
_SKIP_TAXONOMIES = frozenset({"category", "post_tag", "nav_menu", "wp_pattern_category"})
_STATUSES = "publish,future,draft,pending,private"
EXTRAS_LEFT_OUT = (
    "what only WordPress's own exporter carries: custom fields REST does not show, comment, "
    "term and user meta, post passwords, and serialised plugin settings"
)


@dataclass(frozen=True)
class Scope:
    """What to export: everything, posts, pages, a date range (``YYYY-MM-DD``) or a category."""

    kind: str = "everything"
    after: str = ""
    before: str = ""
    category: int = 0
    category_name: str = ""

    def words(self) -> str:
        if self.kind == "dates":
            return f"posts and pages from {self.after or 'the start'} to {self.before or 'today'}"
        if self.kind == "category":
            return f"posts in the category {self.category_name or self.category}"
        return {"posts": "posts", "pages": "pages"}.get(self.kind, "everything")


@dataclass
class ExportReport:
    """Counts by kind, and the left-out lines."""

    counts: dict[str, int] = field(default_factory=dict)
    left_out: list[str] = field(default_factory=list)

    def add(self, kind: str, n: int = 1) -> None:
        self.counts[kind] = self.counts.get(kind, 0) + n

    def sentence(self, name: str) -> str:
        parts = [f"{n} {k}" for k, n in self.counts.items() if n]
        return f"Wrote {name}: {', '.join(parts) or 'nothing'}."


# -- writing ---------------------------------------------------------------------------


def _cdata(text: Any) -> str:
    return "<![CDATA[" + str(text or "").replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _tag(name: str, value: Any, *, cdata: bool = False) -> str:
    body = _cdata(value) if cdata else escape(str("" if value is None else value))
    return f"<{name}>{body}</{name}>"


def _wp_date(value: Any) -> str:
    return str(value or "").replace("T", " ")[:19]


def _rss_date(value: Any) -> str:
    try:
        when = datetime.fromisoformat(str(value)).replace(tzinfo=UTC)
    except ValueError:
        return ""
    return when.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _meta_value(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


class _Reader:
    """Reads one site with the fallbacks REST needs, recording what it could not read."""

    def __init__(self, api: WordPressApi, report: ExportReport) -> None:
        self.api = api
        self.report = report

    def rows(
        self, route: str, params: Mapping[str, Any], what: str, *, fallback: bool = True
    ) -> Iterator[dict[str, Any]]:
        """Every row, edit context first, then (with *fallback*) the public view.

        Stops at :data:`MAX_ROWS`; every fallback, failure and truncation is noted.
        """
        attempts = [dict(params)]
        if fallback:
            view = {**params, "context": "view"}
            if "status" in view:
                view["status"] = "publish"
            attempts.append(view)
        for number, attempt in enumerate(attempts):
            count = 0
            try:
                for raw in self.api.iter_collection(route, attempt):
                    if count >= MAX_ROWS:
                        self.report.left_out.append(
                            f"{what} past the first {MAX_ROWS}: the file stops there"
                        )
                        return
                    count += 1
                    yield raw
                return
            except WordPressApiError as exc:
                if count:  # a failure part-way is said, not retried
                    self.report.left_out.append(f"{what} after the first {count}: {exc.plain}")
                    return
                if number == len(attempts) - 1:
                    self.report.left_out.append(f"{what}: the account may not read them")
                    return
                self.report.left_out.append(
                    f"{what} that are not published: the account may not read drafts, "
                    "private or scheduled ones"
                    if "status" in params
                    else f"{what}: read in their public form only, without private details"
                )

    def get(self, route: str, **params: Any) -> Any:
        try:
            return self.api.get(route, **params)
        except WordPressApiError:
            return None


def _channel_head(out: IO[str], index: Mapping[str, Any], api: WordPressApi) -> None:
    url = str(index.get("url") or api.address.site_url).rstrip("/")
    home = str(index.get("home") or url).rstrip("/")
    out.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    out.write("<!-- WordPress eXtended RSS file, written by QUILL from the site's REST API. -->\n")
    out.write('<rss version="2.0"')
    for prefix, uri in NS.items():
        out.write(f"\n\txmlns:{prefix}={quoteattr(uri)}")
    out.write(">\n<channel>\n")
    out.write(_tag("title", index.get("name", "")) + "\n")
    out.write(_tag("link", home) + "\n")
    out.write(_tag("description", index.get("description", "")) + "\n")
    out.write(_tag("pubDate", datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")) + "\n")
    out.write(_tag("language", index.get("language", "") or "en-US") + "\n")
    out.write(_tag("wp:wxr_version", "1.2") + "\n")
    out.write(_tag("wp:base_site_url", url) + "\n")
    out.write(_tag("wp:base_blog_url", home) + "\n")


@dataclass
class _Site:
    """What the items need to name: people by id, terms by id, files by id."""

    authors: dict[int, dict[str, Any]] = field(default_factory=dict)
    terms: dict[str, dict[int, dict[str, Any]]] = field(default_factory=dict)
    bases: dict[str, str] = field(default_factory=dict)  # taxonomy -> rest_base
    used_authors: set[int] = field(default_factory=set)
    used_terms: set[tuple[str, int]] = field(default_factory=set)
    used_media: set[int] = field(default_factory=set)
    item_ids: set[int] = field(default_factory=set)


def _read_people_and_terms(reader: _Reader, site: _Site) -> None:
    for raw in reader.rows("wp/v2/users", {"context": "edit"}, "people"):
        site.authors[int(raw.get("id", 0) or 0)] = raw
    taxonomies = reader.get("wp/v2/taxonomies") or {}
    site.bases = {"category": "categories", "post_tag": "tags"}
    for slug, tax in taxonomies.items() if isinstance(taxonomies, Mapping) else ():
        if slug not in _SKIP_TAXONOMIES and isinstance(tax, Mapping) and tax.get("rest_base"):
            if str(tax.get("rest_namespace", "wp/v2") or "wp/v2") == "wp/v2":
                site.bases[str(slug)] = str(tax["rest_base"])
    for slug, base in site.bases.items():
        site.terms[slug] = {
            int(t.get("id", 0) or 0): t
            for t in reader.rows(f"wp/v2/{base}", {"context": "edit"}, f"{slug} terms")
        }


def _write_terms(out: IO[str], site: _Site, *, only_used: bool) -> int:
    written = 0
    for taxonomy, terms in site.terms.items():
        for ident, term in terms.items():
            if only_used and (taxonomy, ident) not in site.used_terms:
                continue
            parent = terms.get(int(term.get("parent", 0) or 0), {})
            slug, name = term.get("slug", ""), term.get("name", "")
            description = term.get("description", "")
            if taxonomy == "category":
                out.write(
                    "\t<wp:category>"
                    + _tag("wp:term_id", ident)
                    + _tag("wp:category_nicename", slug, cdata=True)
                    + _tag("wp:category_parent", parent.get("slug", ""), cdata=True)
                    + _tag("wp:cat_name", name, cdata=True)
                    + _tag("wp:category_description", description, cdata=True)
                    + "</wp:category>\n"
                )
            elif taxonomy == "post_tag":
                out.write(
                    "\t<wp:tag>"
                    + _tag("wp:term_id", ident)
                    + _tag("wp:tag_slug", slug, cdata=True)
                    + _tag("wp:tag_name", name, cdata=True)
                    + _tag("wp:tag_description", description, cdata=True)
                    + "</wp:tag>\n"
                )
            else:
                out.write(_term(taxonomy, ident, slug, parent.get("slug", ""), name, description))
            written += 1
    return written


def _term(taxonomy: str, ident: int, slug: str, parent: str, name: str, about: str) -> str:
    return (
        "\t<wp:term>"
        + _tag("wp:term_id", ident)
        + _tag("wp:term_taxonomy", taxonomy, cdata=True)
        + _tag("wp:term_slug", slug, cdata=True)
        + _tag("wp:term_parent", parent, cdata=True)
        + _tag("wp:term_name", name, cdata=True)
        + _tag("wp:term_description", about, cdata=True)
        + "</wp:term>\n"
    )


def _write_authors(out: IO[str], site: _Site, *, only_used: bool) -> int:
    written = 0
    for ident, person in site.authors.items():
        if only_used and ident not in site.used_authors:
            continue
        out.write(
            "\t<wp:author>"
            + _tag("wp:author_id", ident)
            + _tag("wp:author_login", person.get("username") or person.get("slug", ""), cdata=True)
            + _tag("wp:author_email", person.get("email", ""), cdata=True)
            + _tag("wp:author_display_name", person.get("name", ""), cdata=True)
            + _tag("wp:author_first_name", person.get("first_name", ""), cdata=True)
            + _tag("wp:author_last_name", person.get("last_name", ""), cdata=True)
            + "</wp:author>\n"
        )
        written += 1
    return written


def _login(site: _Site, ident: int) -> str:
    person = site.authors.get(ident, {})
    return str(person.get("username") or person.get("slug") or "")


def _guid(raw: Mapping[str, Any]) -> str:
    return str(rendered(raw.get("guid")) or raw.get("link", "") or "")


def _item(
    raw: Mapping[str, Any], post_type: str, site: _Site, comments: list[Mapping[str, Any]]
) -> str:
    ident = int(raw.get("id", 0) or 0)
    status = "inherit" if post_type == "attachment" else str(raw.get("status", "") or "publish")
    parts = [
        _tag("title", raw_text(raw.get("title")) or rendered(raw.get("title"))),
        _tag("link", raw.get("link", "")),
        _tag("pubDate", _rss_date(raw.get("date_gmt"))),
        _tag("dc:creator", _login(site, int(raw.get("author", 0) or 0)), cdata=True),
        f'<guid isPermaLink="false">{escape(_guid(raw))}</guid>',
        _tag("description", ""),
        _tag("content:encoded", raw_text(raw.get("content")), cdata=True),
        _tag("excerpt:encoded", raw_text(raw.get("excerpt")), cdata=True),
        _tag("wp:post_id", ident),
        _tag("wp:post_date", _wp_date(raw.get("date")), cdata=True),
        _tag("wp:post_date_gmt", _wp_date(raw.get("date_gmt")), cdata=True),
        _tag("wp:post_modified", _wp_date(raw.get("modified")), cdata=True),
        _tag("wp:post_modified_gmt", _wp_date(raw.get("modified_gmt")), cdata=True),
        _tag("wp:comment_status", raw.get("comment_status", "closed"), cdata=True),
        _tag("wp:ping_status", raw.get("ping_status", "closed"), cdata=True),
        _tag("wp:post_name", raw.get("slug", ""), cdata=True),
        _tag("wp:status", status, cdata=True),
        _tag("wp:post_parent", int(raw.get("parent", 0) or raw.get("post", 0) or 0)),
        _tag("wp:menu_order", int(raw.get("menu_order", 0) or 0)),
        _tag("wp:post_type", post_type, cdata=True),
        _tag("wp:post_password", "", cdata=True),
        _tag("wp:is_sticky", 1 if raw.get("sticky") else 0),
    ]
    if post_type == "attachment":
        parts.append(_tag("wp:attachment_url", raw.get("source_url", ""), cdata=True))
    for taxonomy, base in site.bases.items():
        for term_id in raw.get(base, []) or []:
            term = site.terms.get(taxonomy, {}).get(int(term_id), {})
            if term:
                domain = "post_tag" if taxonomy == "post_tag" else taxonomy
                parts.append(
                    f"<category domain={quoteattr(domain)} nicename="
                    f"{quoteattr(str(term.get('slug', '')))}>{_cdata(term.get('name', ''))}"
                    "</category>"
                )
    meta = dict(raw.get("meta") or {}) if isinstance(raw.get("meta"), Mapping) else {}
    if int(raw.get("featured_media", 0) or 0):
        meta["_thumbnail_id"] = str(raw["featured_media"])
    if post_type == "attachment" and raw.get("alt_text"):
        meta["_wp_attachment_image_alt"] = raw["alt_text"]
    for key, value in meta.items():
        if value in ("", None, [], {}):
            continue
        parts.append(
            "<wp:postmeta>"
            + _tag("wp:meta_key", key, cdata=True)
            + _tag("wp:meta_value", _meta_value(value), cdata=True)
            + "</wp:postmeta>"
        )
    for comment in comments:
        parts.append(_comment(comment))
    return "\t<item>\n\t\t" + "\n\t\t".join(parts) + "\n\t</item>\n"


def _comment(raw: Mapping[str, Any]) -> str:
    approved = {"approved": "1", "hold": "0", "spam": "spam", "trash": "trash"}
    return (
        "<wp:comment>"
        + _tag("wp:comment_id", int(raw.get("id", 0) or 0))
        + _tag("wp:comment_author", raw.get("author_name", ""), cdata=True)
        + _tag("wp:comment_author_email", raw.get("author_email", ""), cdata=True)
        + _tag("wp:comment_author_url", raw.get("author_url", ""))
        + _tag("wp:comment_author_IP", raw.get("author_ip", ""), cdata=True)
        + _tag("wp:comment_date", _wp_date(raw.get("date")), cdata=True)
        + _tag("wp:comment_date_gmt", _wp_date(raw.get("date_gmt")), cdata=True)
        + _tag(
            "wp:comment_content",
            raw_text(raw.get("content")) or rendered(raw.get("content")),
            cdata=True,
        )
        + _tag("wp:comment_approved", approved.get(str(raw.get("status")), "1"), cdata=True)
        + _tag("wp:comment_type", raw.get("type", "") if raw.get("type") != "comment" else "")
        + _tag("wp:comment_parent", int(raw.get("parent", 0) or 0))
        + _tag("wp:comment_user_id", int(raw.get("author", 0) or 0))
        + "</wp:comment>"
    )


def _types(reader: _Reader, scope: Scope) -> list[tuple[str, str]]:
    """(post type, route) pairs to export, in WordPress's order."""
    if scope.kind in ("posts", "category"):
        return [("post", "wp/v2/posts")]
    if scope.kind == "pages":
        return [("page", "wp/v2/pages")]
    if scope.kind == "dates":
        return [("post", "wp/v2/posts"), ("page", "wp/v2/pages")]
    found = [("post", "wp/v2/posts"), ("page", "wp/v2/pages"), ("wp_block", "wp/v2/blocks")]
    types = reader.get("wp/v2/types") or {}
    for slug, info in types.items() if isinstance(types, Mapping) else ():
        if slug in _SKIP_TYPES or slug in ("post", "page", "wp_block"):
            continue
        if not isinstance(info, Mapping) or not info.get("rest_base"):
            continue
        namespace = str(info.get("rest_namespace", "wp/v2") or "wp/v2")
        found.append((str(slug), f"{namespace}/{info['rest_base']}"))
    return found


def _comments_by_post(reader: _Reader) -> dict[int, list[Mapping[str, Any]]]:
    found: dict[int, list[Mapping[str, Any]]] = {}
    for status in ("approve", "hold"):
        params = {"context": "edit", "status": status}
        for raw in reader.rows(
            "wp/v2/comments", params, f"comments ({status})", fallback=status == "approve"
        ):
            found.setdefault(int(raw.get("post", 0) or 0), []).append(raw)
    return found


def export_wxr(api: WordPressApi, path: Path, scope: Scope | None = None) -> ExportReport:
    """Write one site to *path* as WXR 1.2; the counts and what was left out.

    The file is written to a temporary name beside *path* and moved into place
    only when it is complete, so a failed export never leaves half a file.
    """
    scope = scope or Scope()
    report = ExportReport()
    reader = _Reader(api, report)
    index = reader.get("") or {}
    site = _Site()
    _read_people_and_terms(reader, site)
    comments = _comments_by_post(reader) if scope.kind == "everything" else {}
    only_used = scope.kind != "everything"
    items_tmp = path.with_name(path.name + ".items.part")
    final_tmp = path.with_name(path.name + ".part")
    try:
        with items_tmp.open("w", encoding="utf-8", newline="\n") as body:
            for post_type, route in _types(reader, scope):
                params: dict[str, Any] = {"context": "edit", "status": _STATUSES}
                if scope.kind == "dates":
                    if scope.after:
                        params["after"] = f"{scope.after}T00:00:00"
                    if scope.before:
                        params["before"] = f"{scope.before}T23:59:59"
                if scope.kind == "category":
                    params["categories"] = scope.category
                for raw in reader.rows(route, params, f"{post_type} items"):
                    _note_used(raw, site)
                    ident = int(raw.get("id", 0) or 0)
                    body.write(_item(raw, post_type, site, comments.get(ident, [])))
                    report.add(post_type)
                    report.add("comments", len(comments.get(ident, [])))
            _write_media(reader, body, site, report, only_used=only_used)
            if scope.kind == "everything":
                _write_menus(reader, body, report)
        with final_tmp.open("w", encoding="utf-8", newline="\n") as out:
            _channel_head(out, index if isinstance(index, Mapping) else {}, api)
            report.add("authors", _write_authors(out, site, only_used=only_used))
            report.add("terms", _write_terms(out, site, only_used=only_used))
            if scope.kind == "everything":
                for menu in _menus(reader):
                    out.write(_term("nav_menu", int(menu.get("id", 0) or 0),
                                    str(menu.get("slug", "")), "", str(menu.get("name", "")),
                                    str(menu.get("description", ""))))  # fmt: skip
            out.write(_tag("generator", "QUILL") + "\n")
            with items_tmp.open(encoding="utf-8") as body_in:
                for line in body_in:
                    out.write(line)
            out.write("</channel>\n</rss>\n")
        final_tmp.replace(path)
    finally:
        items_tmp.unlink(missing_ok=True)
        final_tmp.unlink(missing_ok=True)
    if scope.kind != "everything":
        report.left_out.append("comments and menus: only an Everything export carries them")
    report.left_out.append(EXTRAS_LEFT_OUT)
    report.left_out.append(
        "structured custom field values are written as JSON text, which WordPress's "
        "importer keeps as text"
    )
    return report


def _note_used(raw: Mapping[str, Any], site: _Site) -> None:
    site.item_ids.add(int(raw.get("id", 0) or 0))
    site.used_authors.add(int(raw.get("author", 0) or 0))
    if int(raw.get("featured_media", 0) or 0):
        site.used_media.add(int(raw["featured_media"]))
    for taxonomy, base in site.bases.items():
        for term_id in raw.get(base, []) or []:
            site.used_terms.add((taxonomy, int(term_id)))
            parent = site.terms.get(taxonomy, {}).get(int(term_id), {}).get("parent", 0)
            while parent:
                site.used_terms.add((taxonomy, int(parent)))
                parent = site.terms.get(taxonomy, {}).get(int(parent), {}).get("parent", 0)


def _write_media(
    reader: _Reader, out: IO[str], site: _Site, report: ExportReport, *, only_used: bool
) -> None:
    for raw in reader.rows("wp/v2/media", {"context": "edit"}, "media files"):
        ident, parent = int(raw.get("id", 0) or 0), int(raw.get("post", 0) or 0)
        if only_used and ident not in site.used_media and parent not in site.item_ids:
            continue
        site.used_authors.add(int(raw.get("author", 0) or 0))
        out.write(_item(raw, "attachment", site, []))
        report.add("attachments")


def _menus(reader: _Reader) -> list[Mapping[str, Any]]:
    menus = reader.get("wp/v2/menus", context="edit", per_page=100)
    return [m for m in menus or [] if isinstance(m, Mapping)]


def _write_menus(reader: _Reader, out: IO[str], report: ExportReport) -> None:
    menus = {int(m.get("id", 0) or 0): m for m in _menus(reader)}
    if not menus:
        report.left_out.append(
            "menus: the site has none, or the account may not read wp/v2/menus "
            "(it needs edit_theme_options)"
        )
        return
    for raw in reader.rows("wp/v2/menu-items", {"context": "edit"}, "menu items"):
        menu = menus.get(int(raw.get("menus", 0) or 0), {})
        title = raw_text(raw.get("title")) or rendered(raw.get("title"))
        meta = {
            "_menu_item_type": raw.get("type", ""),
            "_menu_item_menu_item_parent": str(raw.get("parent", 0) or 0),
            "_menu_item_object_id": str(raw.get("object_id", 0) or 0),
            "_menu_item_object": raw.get("object", ""),
            "_menu_item_target": raw.get("target", ""),
            "_menu_item_classes": " ".join(raw.get("classes", []) or []),
            "_menu_item_xfn": " ".join(raw.get("xfn", []) or []),
            "_menu_item_url": raw.get("url", ""),
        }
        parts = [
            _tag("title", title),
            _tag("wp:post_id", int(raw.get("id", 0) or 0)),
            _tag("wp:status", "publish", cdata=True),
            _tag("wp:menu_order", int(raw.get("menu_order", 0) or 0)),
            _tag("wp:post_type", "nav_menu_item", cdata=True),
            f'<category domain="nav_menu" nicename={quoteattr(str(menu.get("slug", "")))}>'
            f"{_cdata(menu.get('name', ''))}</category>",
            *(
                "<wp:postmeta>"
                + _tag("wp:meta_key", k, cdata=True)
                + _tag("wp:meta_value", v, cdata=True)
                + "</wp:postmeta>"
                for k, v in meta.items()
            ),
        ]
        out.write("\t<item>\n\t\t" + "\n\t\t".join(parts) + "\n\t</item>\n")
        report.add("menu items")
