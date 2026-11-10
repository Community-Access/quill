"""Things in their own places, within a site and across sites (PRD 15.12; W8).

**Within one site** (:func:`scan_site`, :func:`kind_rows`): every value of a
kind gets its own row, wherever it is used, read from one pass over the
site's posts and pages:

- ``terms``: every term of every taxonomy, "accessibility: 48 posts";
- ``fields``: every custom field value, "Venue: Main Hall, on 31 items";
- ``authors``: "Sam: 120 posts, 4 drafts";
- ``media_usage``: "logo.png: used on 14 pages";
- ``patterns``: synced patterns, "Footer: used on 3 pages";
- ``links``: "https://old.example.org: linked from 22 pages";
- ``blocks``: blocks and shortcodes, "Columns block: on 40 pages";
- ``forms``: forms placed in content, "Form 4: on 5 pages".

**Across sites** (:func:`across_rows`): the same name on many sites, over
every site or a Site Set: terms by name, plugins, themes, users and
settings. Each row says where the copies differ ("Events: on 4 sites, 2
slugs"), and carries its **Variants** (each version and the sites with it)
and **Missing From** (the sites without it). :func:`fleet_rows` is the Fleet
view, every site in one list read row by row. :func:`same_everywhere_plan`
is "make them the same": the chosen variant, previewed site by site.

Wx-free; requests go through each site's own client.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "ACROSS_KINDS",
    "SITE_KINDS",
    "Across",
    "SiteScan",
    "across_rows",
    "fleet_rows",
    "gather_across",
    "kind_rows",
    "same_everywhere_plan",
    "scan_site",
]

SITE_KINDS: Mapping[str, str] = {
    "terms": "Every Term",
    "fields": "Field Values",
    "authors": "Authors",
    "media_usage": "Media Usage",
    "patterns": "Patterns Used",
    "links": "Links",
    "blocks": "Blocks and Shortcodes",
    "forms": "Forms Used",
}

ACROSS_KINDS: Mapping[str, str] = {
    "terms": "Tags and Categories",
    "plugins": "Plugins",
    "themes": "Themes",
    "users": "People",
    "settings": "Settings",
}

_HREF = re.compile(r"""href=["']([^"'#]+)["']""", re.IGNORECASE)
_BLOCK = re.compile(r"<!--\s+wp:([a-z0-9/-]+)(\s+(\{.*?\}))?\s+/?-->")
_SHORTCODE = re.compile(r"\[([a-z][a-z0-9_-]*)[\s\]]")
_REF = re.compile(r'"ref"\s*:\s*(\d+)')
_FORM = re.compile(r'(?:qaf|baf)/form\s+\{[^}]*"(?:formId|id)"\s*:\s*(\d+)')


@dataclass
class SiteScan:
    """One pass over a site's posts and pages, and its terms, media and people."""

    site: str
    items: list[Mapping[str, Any]] = field(default_factory=list)
    terms: list[tuple[str, Mapping[str, Any]]] = field(default_factory=list)
    media: list[Mapping[str, Any]] = field(default_factory=list)
    users: dict[int, str] = field(default_factory=dict)
    patterns: dict[int, str] = field(default_factory=dict)


def _all(api: WordPressApi, route: str, params: Mapping[str, object], pages: int) -> list[Any]:
    try:
        return list(api.iter_collection(route, params, per_page=100, max_pages=pages))
    except WordPressApiError:
        return []


def scan_site(api: WordPressApi, site: str, *, pages: int = 10) -> SiteScan:
    """Read what the within-site kinds need, a page of a hundred at a time."""
    scan = SiteScan(site)
    for kind in ("posts", "pages"):
        for raw in _all(
            api,
            f"wp/v2/{kind}",
            {
                "context": "edit",
                "status": "any",
                "_fields": "id,title,type,status,content,"
                "link,author,meta,featured_media,modified_gmt,slug",
            },
            pages,
        ):
            scan.items.append(raw)
    for taxonomy, route in (("category", "wp/v2/categories"), ("post_tag", "wp/v2/tags")):
        for raw in _all(api, route, {"hide_empty": False}, pages):
            scan.terms.append((taxonomy, raw))
    scan.media = _all(
        api,
        "wp/v2/media",
        {"_fields": "id,title,source_url,media_details,mime_type,post,alt_text,description"},
        pages,
    )
    scan.users = {
        int(u.get("id", 0)): str(u.get("name", ""))
        for u in _all(api, "wp/v2/users", {"_fields": "id,name"}, pages)
    }
    scan.patterns = {
        int(p.get("id", 0)): raw_text(p.get("title")) or rendered(p.get("title"))
        for p in _all(api, "wp/v2/blocks", {"context": "edit", "_fields": "id,title"}, pages)
    }
    return scan


def _content(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("content")) or rendered(raw.get("content"))


def _title(raw: Mapping[str, Any]) -> str:
    return raw_text(raw.get("title")) or rendered(raw.get("title")) or f"#{raw.get('id', '')}"


def _row(
    site: str, kind: str, key: str, name: str, count: int, where: str, places: list[str]
) -> WbRow:
    noun = "place" if count == 1 else "places"
    detail = f"{name}: {where}." if where else f"{name}: in {count} {noun}."
    if places:
        detail += " Used on: " + "; ".join(places[:20]) + ("..." if len(places) > 20 else "")
    return WbRow(
        "value",
        site,
        key,
        {"value": name, "used": where or f"{count} {noun}", "count": str(count)},
        detail,
        subkind=kind,
        raw={"places": places},
    )


def kind_rows(scan: SiteScan, kind: str) -> list[WbRow]:
    """The rows of one within-site kind, most used first."""
    site = scan.site
    rows: list[WbRow] = []
    if kind == "terms":
        for taxonomy, raw in scan.terms:
            count = int(raw.get("count", 0) or 0)
            word = "category" if taxonomy == "category" else "tag"
            name = str(raw.get("name", ""))
            rows.append(
                _row(
                    site,
                    kind,
                    f"{taxonomy}:{raw.get('id')}",
                    f"{name} ({word})",
                    count,
                    f"{count} posts",
                    [],
                )
            )
    elif kind == "authors":
        written: dict[int, Counter[str]] = defaultdict(Counter)
        for raw in scan.items:
            written[int(raw.get("author", 0) or 0)][str(raw.get("status", ""))] += 1
        for author, counts in written.items():
            name = scan.users.get(author, f"person {author}")
            said = ", ".join(f"{n} {s}" for s, n in counts.most_common())
            rows.append(_row(site, kind, str(author), name, sum(counts.values()), said, []))
    else:
        found: dict[str, list[str]] = defaultdict(list)
        for raw in scan.items:
            text, title = _content(raw), _title(raw)
            values: set[str] = set()
            if kind == "fields":
                meta = raw.get("meta")
                for key, value in meta.items() if isinstance(meta, dict) else ():
                    if value not in ("", None, [], {}) and not str(key).startswith("_"):
                        values.add(f"{key}: {value}")
            elif kind == "media_usage":
                for media in scan.media:
                    url = str(media.get("source_url", "") or "")
                    stem = url.rsplit(".", 1)[0] if url else ""
                    if (stem and stem in text) or int(raw.get("featured_media", 0) or 0) == int(
                        media.get("id", -1)
                    ):
                        values.add(url.rsplit("/", 1)[-1])
            elif kind == "patterns":
                for ref in _REF.findall(text):
                    values.add(scan.patterns.get(int(ref), f"pattern {ref}"))
            elif kind == "links":
                values.update(_HREF.findall(text))
            elif kind == "blocks":
                values.update(f"{name} block" for name, _a, _b in _BLOCK.findall(text))
                values.update(f"[{code}] shortcode" for code in _SHORTCODE.findall(text))
            elif kind == "forms":
                values.update(f"Form {ident}" for ident in _FORM.findall(text))
            for value in values:
                found[value].append(title)
        if kind == "media_usage":
            for media in scan.media:
                name = str(media.get("source_url", "") or "").rsplit("/", 1)[-1]
                found.setdefault(name, [])
        for value, places in found.items():
            count = len(places)
            where = f"used on {count} pages" if count else "not used anywhere"
            rows.append(_row(site, kind, value, value, count, where, places))
    rows.sort(key=lambda r: -int(r.cell("count") or 0))
    return rows


# -- across sites -------------------------------------------------------------------


@dataclass
class Across:
    """One name across sites: its variants and the sites missing it."""

    kind: str
    name: str
    variants: dict[str, list[str]]  # variant words -> sites with it
    missing: list[str]
    raw: dict[str, Mapping[str, Any]] = field(default_factory=dict)  # site -> object

    @property
    def sites(self) -> list[str]:
        return sorted({s for group in self.variants.values() for s in group})

    @property
    def sentence(self) -> str:
        count = len(self.sites)
        said = f"{self.name}: on {count} site{'s' if count != 1 else ''}"
        if len(self.variants) > 1:
            said += f", {len(self.variants)} versions"
        if self.missing:
            said += f", missing from {len(self.missing)}"
        return said


def _plugin_name(raw: Mapping[str, Any]) -> str:
    name = raw.get("name")
    return str(
        name.get("rendered", "") if isinstance(name, dict) else name or raw.get("plugin", "")
    )


def gather_across(
    kind: str, sites: Sequence[tuple[str, WordPressApi]]
) -> dict[str, dict[str, Mapping[str, Any]]]:
    """For *kind*, each name and, by site, the object that site has under it."""
    found: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for site, api in sites:
        if kind == "terms":
            for word, route in (("category", "wp/v2/categories"), ("tag", "wp/v2/tags")):
                for raw in _all(api, route, {"hide_empty": False}, 5):
                    found[f"{raw.get('name', '')} ({word})"][site] = raw
        elif kind == "plugins":
            for raw in _all(api, "wp/v2/plugins", {}, 2):
                found[_plugin_name(raw)][site] = raw
        elif kind == "themes":
            for raw in _all(api, "wp/v2/themes", {}, 2):
                name = raw.get("name")
                found[str(name.get("rendered", "") if isinstance(name, dict) else name)][site] = raw
        elif kind == "users":
            for raw in _all(api, "wp/v2/users", {"context": "edit"}, 5):
                key = str(raw.get("email") or raw.get("username") or raw.get("name", ""))
                found[key][site] = raw
        elif kind == "settings":
            try:
                settings = api.get("wp/v2/settings")
            except WordPressApiError:
                settings = {}
            for key, value in settings.items() if isinstance(settings, dict) else ():
                found[str(key)][site] = {"value": value}
    return dict(found)


def _variant(kind: str, raw: Mapping[str, Any]) -> str:
    if kind == "terms":
        return f"slug {raw.get('slug', '')}"
    if kind == "plugins":
        return f"version {raw.get('version', '')}, {raw.get('status', '')}"
    if kind == "themes":
        return f"version {raw.get('version', '')}, {raw.get('status', '')}"
    if kind == "users":
        roles = raw.get("roles") or []
        return f"{roles[0] if roles else 'no role'}"
    return str(raw.get("value"))


def across_rows(
    kind: str, found: Mapping[str, Mapping[str, Mapping[str, Any]]], every_site: Sequence[str]
) -> list[WbRow]:
    """One row per name: where it is, how the copies differ, and where it is missing."""
    rows: list[WbRow] = []
    for name, by_site in sorted(found.items(), key=lambda kv: (-len(kv[1]), kv[0].casefold())):
        variants: dict[str, list[str]] = defaultdict(list)
        for site, raw in by_site.items():
            variants[_variant(kind, raw)].append(site)
        missing = [s for s in every_site if s not in by_site]
        item = Across(kind, name, dict(variants), missing, dict(by_site))
        lines = [f"{words}: {', '.join(sorted(sites))}" for words, sites in item.variants.items()]
        detail = item.sentence + ". Variants: " + "; ".join(lines)
        if missing:
            detail += ". Missing from: " + ", ".join(missing)
        rows.append(
            WbRow(
                "across",
                "",
                name,
                {
                    "name": name,
                    "sites": str(len(item.sites)),
                    "versions": str(len(item.variants)),
                    "missing": ", ".join(missing),
                },
                detail + ".",
                subkind=kind,
                raw={"variants": item.variants, "missing": missing, "objects": item.raw},
            )
        )
    return rows


def same_everywhere_plan(row: WbRow, variant: str) -> list[tuple[str, str]]:
    """(site, what will happen) for making every site match *variant* of *row*."""
    variants: Mapping[str, list[str]] = row.raw.get("variants") or {}
    missing: list[str] = list(row.raw.get("missing") or [])
    plan: list[tuple[str, str]] = []
    for words, sites in variants.items():
        for site in sites:
            if words == variant:
                plan.append((site, "already matches; nothing to do"))
            else:
                plan.append((site, f"changes from {words} to {variant}"))
    for site in missing:
        plan.append((site, f"gets {row.key}, as {variant}"))
    return plan


def fleet_rows(facts: Iterable[tuple[str, Mapping[str, Any]]]) -> list[WbRow]:
    """The Fleet view: every site in one list, read row by row."""
    rows: list[WbRow] = []
    for site, fact in facts:
        parts = [f"WordPress {fact.get('version') or 'version not said'}"]
        if fact.get("waiting") is not None:
            parts.append(f"{fact['waiting']} comments waiting")
        if fact.get("plugins") is not None:
            parts.append(f"{fact['plugins']} plugins")
        if fact.get("health"):
            parts.append(f"health {fact['health']}")
        if fact.get("error"):
            parts = [f"not answering: {fact['error']}"]
        rows.append(
            WbRow(
                "fleet",
                site,
                site,
                {"site": site, "state": ", ".join(parts)},
                f"{site}: {', '.join(parts)}.",
            )
        )
    return rows
