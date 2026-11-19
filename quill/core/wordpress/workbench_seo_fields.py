"""Yoast SEO's canonical address, primary category and schema type, on a post's sheet.

Properties on a post or page (and on a row of the SEO node) has an **SEO**
page wherever the site's REST index lists ``yoast/v1``. It holds four of
Yoast's per-post settings:

- **Canonical address**, **Primary category** (posts, chosen by name from the
  post's own categories), **Schema page type** and **Schema article type**.

Yoast keeps them in post meta. Its bulk editor routes
(:mod:`quill.core.wordpress.workbench_seo_bulk`) carry only the SEO title,
description, focus keyphrase and social title and description, and none of
the 61 ``yoast/v1`` routes in the WordPress PRD's Appendix D writes these
four, so the only REST way to change them is the post's own ``wp/v2`` route,
and only for a field the site registers for the REST API. The meta names in
:data:`YOAST_FIELDS` are Yoast's own (``WPSEO_Meta``'s ``canonical``,
``schema_page_type`` and ``schema_article_type``, prefixed ``_yoast_wpseo_``,
and ``WPSEO_Primary_Term``'s ``_yoast_wpseo_primary_category``); one is used
**only when the site's own schema for the post lists it**, so nothing is ever
sent under a name the site has not shown. Most sites do not register them.

Where a field is not registered it is shown read only, from what the site
does say: the canonical address and the schema types from ``yoast_head_json``
(what Yoast gives search engines), and the primary category as not shown. One
sentence on the page says those are changed in the post's Yoast panel, and
**Open in wp-admin** on the row opens the post's editor, where that panel is.
Wx-free and network-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from quill.core.wordpress.workbench_seo import has_yoast
from quill.core.wordpress.workbench_sheet_words import labelled
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec, Value

__all__ = [
    "ARTICLE_TYPES",
    "CANONICAL",
    "PAGE_TYPES",
    "PRIMARY_CATEGORY",
    "SCHEMA_ARTICLE",
    "SCHEMA_PAGE",
    "YOAST_FIELDS",
    "schema_types",
    "seo_page",
    "with_seo_page",
]

CANONICAL = "_yoast_wpseo_canonical"
PRIMARY_CATEGORY = "_yoast_wpseo_primary_category"
SCHEMA_PAGE = "_yoast_wpseo_schema_page_type"
SCHEMA_ARTICLE = "_yoast_wpseo_schema_article_type"

#: Yoast's post meta for the four fields, with how each is named.
YOAST_FIELDS: dict[str, str] = {
    CANONICAL: "Canonical address",
    PRIMARY_CATEGORY: "Primary category",
    SCHEMA_PAGE: "Schema page type",
    SCHEMA_ARTICLE: "Schema article type",
}

#: The page types Yoast's Schema tab offers (``Schema_Types::PAGE_TYPES``).
PAGE_TYPES: tuple[tuple[str, str], ...] = (
    ("WebPage", "Web page"),
    ("ItemPage", "Item page"),
    ("AboutPage", "About page"),
    ("FAQPage", "FAQ page"),
    ("QAPage", "Question and answer page"),
    ("ProfilePage", "Profile page"),
    ("ContactPage", "Contact page"),
    ("MedicalWebPage", "Medical page"),
    ("CollectionPage", "Collection page"),
    ("CheckoutPage", "Checkout page"),
    ("RealEstateListing", "Real estate listing"),
    ("SearchResultsPage", "Search results page"),
)

#: The article types Yoast's Schema tab offers (``Schema_Types::ARTICLE_TYPES``).
ARTICLE_TYPES: tuple[tuple[str, str], ...] = (
    ("Article", "Article"),
    ("BlogPosting", "Blog post"),
    ("SocialMediaPosting", "Social media posting"),
    ("NewsArticle", "News article"),
    ("AdvertiserContentArticle", "Advertiser content article"),
    ("SatiricalArticle", "Satirical article"),
    ("ScholarlyArticle", "Scholarly article"),
    ("TechArticle", "Tech article"),
    ("Report", "Report"),
    ("None", "None"),
)

_DEFAULT = "Default: the content type's setting in Yoast"
_NONE_PRIMARY = "None chosen: Yoast uses the first category"
_RO = "yoast."
"""Read-only fields are keyed apart from ``meta.``, so a save can never send one."""


def _types_in(node: Mapping[str, Any]) -> list[str]:
    kind = node.get("@type")
    if isinstance(kind, str):
        return [kind]
    return [str(k) for k in kind] if isinstance(kind, list) else []


def schema_types(head: Mapping[str, Any]) -> tuple[str, str]:
    """(page type, article type) as Yoast's schema graph in ``yoast_head_json`` says them."""
    schema = head.get("schema")
    graph = schema.get("@graph") if isinstance(schema, Mapping) else None
    pages = dict(PAGE_TYPES)
    articles = {k: v for k, v in ARTICLE_TYPES if k != "None"}
    page = article = ""
    for node in graph if isinstance(graph, list) else []:
        if not isinstance(node, Mapping):
            continue
        kinds = _types_in(node)
        found = [pages[k] for k in kinds if k in pages]
        if found and not page:
            page = found[-1]  # ["WebPage", "FAQPage"]: the narrower one
        named = [articles[k] for k in kinds if k in articles]
        if named and not article:
            article = named[-1]
    return page, article


def _choices(rows: Iterable[tuple[str, str]], enum: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """("", values...) and their words; a registered ``enum`` limits them to what it allows."""
    allowed = {str(v) for v in enum} if isinstance(enum, list) and enum else None
    kept = [(k, w) for k, w in rows if allowed is None or k in allowed]
    return ("", *(k for k, _ in kept)), (_DEFAULT, *(w for _, w in kept))


def _where(names: list[str]) -> str:
    listed = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
    verb = "is" if len(names) == 1 else "are"
    return (
        f"{listed} {verb} changed in this post's Yoast panel in wp-admin, because this site "
        "does not give Yoast's setting for it to the REST API; Open in wp-admin on the post's "
        "row opens its editor there."
    )


def seo_page(
    fresh: Mapping[str, Any],
    meta_schema: Mapping[str, Any],
    categories: Mapping[str, int],
) -> tuple[PageSpec | None, dict[str, Value]]:
    """The SEO page for the post *fresh*, and the values its read-only fields show.

    *meta_schema* is the registered meta of the post's route; *categories* is
    the post's own categories by name (``{"News": 12}``).
    """
    head = fresh.get("yoast_head_json")
    head = head if isinstance(head, Mapping) else {}
    found = fresh.get("meta")
    meta: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
    page_type, article_type = schema_types(head)
    is_post = "categories" in fresh
    fields: list[FieldSpec] = []
    values: dict[str, Value] = {}
    missing: list[str] = []

    def read_only(key: str, value: str, said: str = "as Yoast gives it to search engines") -> None:
        label = YOAST_FIELDS[key]
        fields.append(
            FieldSpec(
                f"{_RO}{key}",
                label,
                FieldKind.TEXT,
                readonly=True,
                help=f"{label}, {said}. " + _where([label]),
            )
        )
        values[f"{_RO}{key}"] = value
        missing.append(label)

    def spec(key: str) -> Mapping[str, Any] | None:
        got = meta_schema.get(key)
        return got if isinstance(got, Mapping) else None

    if spec(CANONICAL) is not None:
        fields.append(
            FieldSpec(
                f"meta.{CANONICAL}",
                YOAST_FIELDS[CANONICAL],
                FieldKind.TEXT,
                help="The address search engines are told is this post's own. Blank uses its "
                "permalink; set it only when the same text lives at another address.",
            )
        )
    else:
        read_only(CANONICAL, str(head.get("canonical", "") or "") or "none given")
    if is_post:
        ids = [int(i) for i in fresh.get("categories") or [] if str(i).isdigit()]
        by_id = {v: k for k, v in categories.items()}
        if spec(PRIMARY_CATEGORY) is not None:
            current = str(meta.get(PRIMARY_CATEGORY, "") or "")
            choices = ["", *(str(i) for i in ids)]
            words = [_NONE_PRIMARY, *(labelled(by_id.get(i, ""), i) for i in ids)]
            if current and current not in choices:  # a category the post no longer has
                choices.append(current)
                words.append(f"Category {current}, no longer one of this post's categories")
            fields.append(
                FieldSpec(
                    f"meta.{PRIMARY_CATEGORY}",
                    YOAST_FIELDS[PRIMARY_CATEGORY],
                    FieldKind.CHOICE,
                    help="The category Yoast puts in this post's breadcrumbs and permalink, "
                    "chosen from its own categories by name.",
                    choices=tuple(choices),
                    choice_words=tuple(words),
                )
            )
        else:
            names = ", ".join(by_id.get(i, str(i)) for i in ids) or "none"
            read_only(
                PRIMARY_CATEGORY,
                f"not shown to the REST API; its categories: {names}",
                "which this site does not show; the post's categories are named instead",
            )
    for key, rows, shown, wanted in (
        (SCHEMA_PAGE, PAGE_TYPES, page_type, True),
        (SCHEMA_ARTICLE, ARTICLE_TYPES, article_type, is_post),
    ):
        registered = spec(key)
        if registered is not None:
            offered, said = _choices(rows, registered.get("enum"))
            fields.append(
                FieldSpec(
                    f"meta.{key}",
                    YOAST_FIELDS[key],
                    FieldKind.CHOICE,
                    help=f"What Yoast's schema calls this post. {_DEFAULT}.",
                    choices=offered,
                    choice_words=said,
                )
            )
        elif wanted:
            read_only(key, shown or "none in its schema")
    if missing:
        fields.append(
            FieldSpec(
                f"{_RO}where",
                "Where these change",
                FieldKind.MULTILINE,
                readonly=True,
                help=_where(missing),
            )
        )
        values[f"{_RO}where"] = _where(missing)
    return (PageSpec("seo", "SEO", tuple(fields)) if fields else None), values


def with_seo_page(
    ctx: Any,
    sheet: SheetSpec,
    values: dict[str, Any],
    fresh: Mapping[str, Any],
    meta_schema: Mapping[str, Any],
    categories: Mapping[str, int],
) -> SheetSpec:
    """*sheet* with its SEO page where the site has Yoast; *values* gains the page's values.

    A registered field moves from the Meta page to the SEO page under the same
    ``meta.`` key, so it saves, verifies and undoes as registered meta does.
    """
    if not has_yoast(ctx):
        return sheet
    page, shown = seo_page(fresh, meta_schema, categories)
    if page is None:
        return sheet
    values.update(shown)
    moved = {f"meta.{key}" for key in YOAST_FIELDS}
    pages: list[PageSpec] = []
    for old in sheet.pages:
        if old.key == "meta":
            kept = tuple(f for f in old.fields if f.key not in moved)
            if not kept:
                continue
            old = PageSpec(old.key, old.title, kept)
        pages.append(old)
    return SheetSpec(sheet.kind, sheet.title, (*pages, page))
