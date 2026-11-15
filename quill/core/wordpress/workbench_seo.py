"""Yoast SEO in the Workbench: per post, and for the whole site (Package 12).

**Per post.** Each post and page carries ``yoast_head_json``, what Yoast
gives search engines, read with ``context=edit`` so the meta Yoast registers
for the REST API comes too. A row says the SEO title and description with
their lengths, whether the item is indexed, and its focus keyphrase.
**Search Appearance** reads what a search engine shows as three lines (title,
address, description), each with where it would be cut off. **Edit SEO**
writes the registered meta fields (:data:`SEO_META`) through the post's own
``wp/v2`` route after a preview; a field this site's Yoast has not registered
for the REST API is named and left for the post's Yoast panel in wp-admin.

**The whole site.** ``yoast/v1/seo_scores`` and ``readability_scores`` for
posts and pages, as words; then every job only Yoast's own screens can do
(:data:`WP_ADMIN_ONLY`), each a row that opens that screen. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import length_note
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "NOINDEX",
    "SEO_META",
    "WP_ADMIN_ONLY",
    "YOAST_NAMESPACE",
    "SeoEdit",
    "load_seo_items",
    "load_seo_site",
    "search_appearance",
    "seo_body",
    "seo_preview",
    "seo_row",
]

YOAST_NAMESPACE = "yoast/v1"
TITLE_LIMIT = 60
DESCRIPTION_LIMIT = 160

#: The post meta Yoast registers, with how each is named.
SEO_META: dict[str, str] = {
    "_yoast_wpseo_title": "SEO title",
    "_yoast_wpseo_metadesc": "Meta description",
    "_yoast_wpseo_focuskw": "Focus keyphrase",
    "_yoast_wpseo_meta-robots-noindex": "Show in search results",
}

#: Yoast's noindex values, as said.
NOINDEX: dict[str, str] = {
    "0": "as the content type's default",
    "1": "no, kept out of search results",
    "2": "yes, shown in search results",
}

#: What only Yoast's screens in wp-admin do: (what, why, wp-admin page).
WP_ADMIN_ONLY: tuple[tuple[str, str, str], ...] = (
    (
        "Search appearance for each content type",
        "Yoast keeps its title templates and defaults in settings with no REST route.",
        "admin.php?page=wpseo_page_settings",
    ),
    (
        "Site representation and social profiles",
        "Only the first-time configuration routes exist; the settings page is browser-only.",
        "admin.php?page=wpseo_page_settings#/site-representation",
    ),
    (
        "Optimise SEO data (indexing)",
        "The indexing routes run in steps from Yoast's own button; QUILL does not start them.",
        "admin.php?page=wpseo_tools",
    ),
    (
        "Redirects, schema and breadcrumbs",
        "Redirects are Yoast SEO Premium's; schema and breadcrumbs are settings pages only.",
        "admin.php?page=wpseo_dashboard",
    ),
    (
        "Related keyphrases and rank tracking",
        "Semrush and Wincher need your own accounts with them, linked in wp-admin.",
        "admin.php?page=wpseo_integrations",
    ),
    (
        "Yoast's AI features",
        "They need a Yoast account; QUILL's own AI covers the writing side.",
        "admin.php?page=wpseo_dashboard",
    ),
)


def has_yoast(ctx: Any) -> bool:
    info = getattr(ctx, "info", None)
    return YOAST_NAMESPACE in tuple(getattr(info, "namespaces", ()) or ())


def _cut(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}... (cut off after {limit} characters)"


def search_appearance(head: Mapping[str, Any], link: str = "") -> list[str]:
    """Title, address and description, as a search engine shows them."""
    title = str(head.get("title", "") or "")
    address = str(head.get("canonical") or head.get("og_url") or link or "")
    description = str(head.get("description") or head.get("og_description") or "")
    return [
        f"Title: {_cut(title, TITLE_LIMIT) or 'none given'}",
        f"Address: {address or 'none given'}",
        f"Description: {_cut(description, DESCRIPTION_LIMIT) or 'none: the engine picks text'}",
    ]


def _indexed(head: Mapping[str, Any]) -> str:
    robots = head.get("robots")
    if isinstance(robots, Mapping) and str(robots.get("index", "")) == "noindex":
        return "not indexed"
    return "indexed"


def seo_row(raw: Mapping[str, Any], site: str) -> WbRow:
    title = rendered(raw.get("title")) or "Untitled"
    head = raw.get("yoast_head_json")
    head = head if isinstance(head, Mapping) else {}
    found = raw.get("meta")
    meta: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
    seo_title = str(head.get("title", "") or "")
    description = str(head.get("description", "") or "")
    keyphrase = str(meta.get("_yoast_wpseo_focuskw", "") or "")
    indexed = _indexed(head)
    problems = []
    if not description:
        problems.append("no meta description")
    if len(seo_title) > TITLE_LIMIT:
        problems.append(f"title over {TITLE_LIMIT} characters")
    if "_yoast_wpseo_focuskw" in meta and not keyphrase:
        problems.append("no focus keyphrase")
    if indexed == "not indexed":
        problems.append("kept out of search results")
    kind = str(raw.get("type", "") or "post")
    return WbRow(
        kind="seo_item",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={
            "title": title,
            "seo_title": seo_title or "not set",
            "description": f"{len(description)} characters" if description else "none",
            "index": indexed,
            "keyphrase": keyphrase
            or ("not set" if "_yoast_wpseo_focuskw" in meta else "not readable"),
        },
        detail=(
            f"{title}, a {kind}. "
            + length_note("SEO title", seo_title, TITLE_LIMIT)
            + ". "
            + length_note("Meta description", description, DESCRIPTION_LIMIT)
            + f". {indexed.capitalize()}. "
            + (f"To look at: {', '.join(problems)}." if problems else "Nothing to look at.")
        ),
        link=str(raw.get("link", "") or ""),
        status=str(raw.get("status", "") or ""),
        subkind=kind,
        raw={
            "title": title,
            "kind": kind,
            "route": f"wp/v2/{'pages' if kind == 'page' else 'posts'}/{raw.get('id', '')}",
            "seo_title": seo_title,
            "description": description,
            "indexed": indexed,
            "keyphrase": keyphrase,
            "meta": {k: str(v) for k, v in meta.items() if k in SEO_META},
            "appearance": "\n".join(search_appearance(head, str(raw.get("link", "") or ""))),
        },
    )


def load_seo_items(ctx: Any, query: Mapping[str, object]) -> list[WbRow]:
    if not has_yoast(ctx):
        raise WordPressApiError(
            f"{ctx.name} does not list Yoast SEO's {YOAST_NAMESPACE} routes in its REST index, "
            "so QUILL has no Yoast SEO to read there. Titles and descriptions another SEO "
            "plugin registers are on each item's Properties."
        )
    rows: list[WbRow] = []
    for base in ("posts", "pages"):
        params: dict[str, object] = {
            "context": "edit",
            "_fields": "id,title,link,type,status,yoast_head_json,meta",
            "orderby": "modified",
            "order": "desc",
        }
        if query.get("search"):
            params["search"] = query["search"]
        found = ctx.api.iter_collection(f"wp/v2/{base}", params, per_page=50, max_pages=2)
        rows += [seo_row(raw, ctx.name) for raw in found if isinstance(raw, dict)]
    return rows


# -- Edit SEO --------------------------------------------------------------------------


@dataclass(frozen=True)
class SeoEdit:
    """What Edit SEO was given; ``None`` leaves a field as it is."""

    title: str | None = None
    description: str | None = None
    keyphrase: str | None = None
    noindex: str | None = None


def seo_body(meta: Mapping[str, str], edit: SeoEdit) -> tuple[dict[str, str], list[str]]:
    """The changed meta Yoast registered on this item, and the names of those it did not."""
    wanted = {
        "_yoast_wpseo_title": edit.title,
        "_yoast_wpseo_metadesc": edit.description,
        "_yoast_wpseo_focuskw": edit.keyphrase,
        "_yoast_wpseo_meta-robots-noindex": edit.noindex,
    }
    changed: dict[str, str] = {}
    unwritable: list[str] = []
    for key, value in wanted.items():
        if value is None or value.strip() == str(meta.get(key, "") or "").strip():
            continue
        if key not in meta:
            unwritable.append(SEO_META[key])
            continue
        changed[key] = value.strip()
    return changed, unwritable


def seo_preview(
    title: str, site: str, meta: Mapping[str, str], body: Mapping[str, str], unwritable: list[str]
) -> list[str]:
    lines = [f"Yoast SEO for {title} on {site}:"]
    for key, value in body.items():
        name = SEO_META[key]
        if key == "_yoast_wpseo_meta-robots-noindex":
            old = NOINDEX.get(str(meta.get(key, "0") or "0"), "as the default")
            lines.append(f"{name}: {old} becomes {NOINDEX.get(value, value)}.")
            continue
        lines.append(f"{name}: {meta.get(key) or 'not set'} becomes {value or 'not set'}.")
        if key == "_yoast_wpseo_title":
            lines.append(length_note("The new SEO title", value, TITLE_LIMIT) + ".")
        if key == "_yoast_wpseo_metadesc":
            lines.append(length_note("The new description", value, DESCRIPTION_LIMIT) + ".")
    if unwritable:
        lines.append(
            f"Not changed: {', '.join(unwritable)}. This site's Yoast has not registered "
            "them for the REST API, so they are changed in the item's Yoast panel in wp-admin."
        )
    lines.append("Yoast recalculates its scores the next time the item is opened in wp-admin.")
    return lines


# -- the whole site -------------------------------------------------------------------

_SCORE_WORDS = {
    "good": "good",
    "ok": "OK",
    "bad": "needs improvement",
    "notAnalyzed": "not analysed",
    "noFocus": "no focus keyphrase",
}


def scores_sentence(answer: Any) -> tuple[str, str]:
    """``{"scores": [{"name": "good", "amount": 4}, ...]}`` -> a sentence and a table."""
    scores = answer.get("scores", []) if isinstance(answer, Mapping) else answer
    parts = []
    for score in scores if isinstance(scores, list) else []:
        if isinstance(score, Mapping):
            name = str(score.get("name", "") or "")
            parts.append(f"{score.get('amount', 0)} {_SCORE_WORDS.get(name, name)}")
    said = ", ".join(parts) or "no scores yet"
    return said, "\n".join(parts)


def load_seo_site(ctx: Any) -> list[WbRow]:
    if not has_yoast(ctx):
        raise WordPressApiError(
            f"{ctx.name} does not list Yoast SEO's {YOAST_NAMESPACE} routes in its REST index."
        )
    rows: list[WbRow] = []
    admin = f"{str(getattr(ctx, 'url', '') or '').rstrip('/')}/wp-admin/"
    for route, what in (("seo_scores", "SEO scores"), ("readability_scores", "Readability")):
        for content_type, plural in (("post", "posts"), ("page", "pages")):
            name = f"{what} for {plural}"
            try:
                answer = ctx.api.get(f"{YOAST_NAMESPACE}/{route}", contentType=content_type)
                said, table = scores_sentence(answer)
            except WordPressApiError as exc:
                said, table = f"not read: {exc.plain}", ""
            rows.append(
                WbRow(
                    kind="seo_score",
                    site=ctx.name,
                    key=f"{route}/{content_type}",
                    cells={"what": name, "says": said},
                    detail=f"{name}: {said}.",
                    link=f"{admin}admin.php?page=wpseo_dashboard",
                    subkind="yoast",
                    raw={"what": name, "says": said, "table": table},
                )
            )
    for what, why, page in WP_ADMIN_ONLY:
        rows.append(
            WbRow(
                kind="dashboard",
                site=ctx.name,
                key=f"yoast/{page}",
                cells={"what": what, "says": f"in wp-admin only. {why}"},
                detail=f"{what}: in wp-admin only. {why} Enter opens it.",
                link=f"{admin}{page}",
                subkind="yoast",
                raw={"what": what, "why": why},
            )
        )
    return rows
