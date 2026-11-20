"""Yoast's per-post canonical, primary category and schema type; WP-Cron beyond posts.

Wx-free and network-free: what the SEO page holds for a site that registers
Yoast's meta and for one that does not (the usual case), that nothing is
keyed so a save could send an unregistered name, and the Search and Upkeep
row for every other WP-Cron task (WP Crontrol has no recorded REST route).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_coverage import (
    THIRD_SWEEP,
    sweep_disposition,
)
from quill.core.wordpress.workbench_seo_bulk import SEARCH_FIELDS, SOCIAL_FIELDS
from quill.core.wordpress.workbench_seo_fields import (
    ARTICLE_TYPES,
    CANONICAL,
    PAGE_TYPES,
    PRIMARY_CATEGORY,
    SCHEMA_ARTICLE,
    SCHEMA_PAGE,
    YOAST_FIELDS,
    canonical_shown,
    schema_types,
    seo_page,
    with_seo_page,
)
from quill.core.wordpress.workbench_upkeep import (
    CRON_EVENTS,
    cron_row,
    crontrol_active,
)
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec

_GRAPH = {
    "schema": {
        "@graph": [
            {"@type": ["WebPage", "AboutPage"]},
            {"@type": "NewsArticle"},
        ]
    },
    "canonical": "https://radio.example/about/",
}


def test_the_bulk_editor_carries_none_of_the_four_fields() -> None:
    # Why these are written only through registered meta: Yoast's bulk editor routes
    # (the recorded yoast/v1 routes that write per post) know only these five.
    carried = set(SEARCH_FIELDS) | set(SOCIAL_FIELDS)
    assert carried == {
        "seo_title",
        "meta_description",
        "focus_keyphrase",
        "social_title",
        "social_description",
    }
    assert not {"canonical", "primary_category", "schema_page_type"} & carried


def test_schema_types_read_the_narrower_page_type_and_the_article_type() -> None:
    assert schema_types(_GRAPH) == ("About page", "News article")
    assert schema_types({}) == ("", "")
    assert schema_types({"schema": {"@graph": ["junk", {"@type": 3}]}}) == ("", "")


def test_a_page_without_registered_meta_is_read_only_with_one_sentence() -> None:
    fresh = {"type": "page", "yoast_head_json": _GRAPH}
    page, values = seo_page(fresh, {}, {})
    assert page is not None
    keys = [f.key for f in page.fields]
    assert keys == [
        f"yoast.{CANONICAL}",
        f"yoast.{SCHEMA_PAGE}",
        "yoast.where",
    ]  # a page has no categories and no article type
    assert all(f.readonly and not f.key.startswith("meta.") for f in page.fields)
    assert values[f"yoast.{CANONICAL}"] == "https://radio.example/about/"
    assert values[f"yoast.{SCHEMA_PAGE}"] == "About page"
    assert values["yoast.where"] == (
        "Canonical address and Schema page type are changed in this post's Yoast panel in "
        "wp-admin, because this site does not give Yoast's setting for it to the REST API; "
        "Open in wp-admin on the post's row opens its editor there."
    )


#: The test site's Welcome post as Yoast SEO 28.9 heads it (2026-11-19), trimmed: the
#: site discourages search engines, so the head is noindex and has no canonical key.
LIVE_HEAD = {
    "title": "Welcome to the QUILL test site - QUILL WordPress Test Site",
    "robots": {"index": "noindex", "follow": "follow"},
    "og_url": "https://lp.csedesigns.com/wordpress/welcome/",
    "schema": {
        "@graph": [
            {"@type": "NewsArticle", "articleSection": ["News", "Training"]},
            {"@type": "WebPage"},
            {"@type": "BreadcrumbList"},
            {"@type": "WebSite"},
            {"@type": "Organization"},
        ]
    },
}
#: The Yoast meta that site registers for REST: three, none of the four on the SEO page.
LIVE_YOAST_META = {
    "_yoast_wpseo_focuskw": {"type": "string", "title": "", "description": "", "default": ""},
    "_yoast_wpseo_title": {"type": "string", "title": "", "description": "", "default": ""},
    "_yoast_wpseo_metadesc": {"type": "string", "title": "", "description": "", "default": ""},
}


def test_a_noindex_post_has_no_canonical_in_its_head_and_its_address_is_said() -> None:
    fresh = {"type": "post", "categories": [3, 7], "yoast_head_json": LIVE_HEAD}
    page, values = seo_page(fresh, LIVE_YOAST_META, {"News": 3, "Training": 7})
    assert page is not None
    assert all(f.readonly for f in page.fields)
    assert values[f"yoast.{CANONICAL}"] == (
        "https://lp.csedesigns.com/wordpress/welcome/, its address; Yoast gives search engines "
        "no canonical address while the post is not indexed"
    )
    assert values[f"yoast.{SCHEMA_PAGE}"] == "Web page"
    assert values[f"yoast.{PRIMARY_CATEGORY}"].endswith("its categories: News, Training")
    assert canonical_shown({}) == "none given"
    assert canonical_shown({"robots": {"index": "noindex"}}).startswith("none: Yoast")


def test_registered_meta_is_editable_and_a_registered_enum_limits_the_choices() -> None:
    fresh = {
        "categories": [5, 9],
        "meta": {PRIMARY_CATEGORY: "9", CANONICAL: "", SCHEMA_PAGE: "", SCHEMA_ARTICLE: ""},
    }
    schema = {
        CANONICAL: {"type": "string"},
        PRIMARY_CATEGORY: {"type": "string"},
        SCHEMA_PAGE: {"type": "string", "enum": ["", "WebPage", "FAQPage"]},
        SCHEMA_ARTICLE: {"type": "string"},
    }
    page, values = seo_page(fresh, schema, {"Shows": 5, "News": 9})
    assert page is not None and not values
    by_key = {f.key: f for f in page.fields}
    assert set(by_key) == {f"meta.{k}" for k in YOAST_FIELDS}
    primary = by_key[f"meta.{PRIMARY_CATEGORY}"]
    assert primary.kind is FieldKind.CHOICE
    assert primary.choices == ("", "5", "9")
    assert primary.word_for("9") == "News (9)"
    assert by_key[f"meta.{SCHEMA_PAGE}"].choices == ("", "WebPage", "FAQPage")
    assert len(by_key[f"meta.{SCHEMA_ARTICLE}"].choices) == len(ARTICLE_TYPES) + 1
    assert by_key[f"meta.{SCHEMA_ARTICLE}"].word_for("").startswith("Default")


def test_a_primary_category_the_post_no_longer_has_is_kept_and_named() -> None:
    fresh = {"categories": [5], "meta": {PRIMARY_CATEGORY: "7"}}
    page, _values = seo_page(fresh, {PRIMARY_CATEGORY: {"type": "string"}}, {"Shows": 5})
    assert page is not None
    primary = page.fields[1]
    assert primary.choices[-1] == "7"
    assert "no longer one of this post's categories" in primary.word_for("7")


def test_with_seo_page_moves_registered_meta_off_the_meta_page() -> None:
    meta_page = PageSpec(
        "meta",
        "Meta",
        (
            FieldSpec(f"meta.{CANONICAL}", CANONICAL),
            FieldSpec("meta.other", "other"),
        ),
    )
    sheet = SheetSpec("item", "Item", (PageSpec("general", "General", ()), meta_page))
    ctx = SimpleNamespace(info=SimpleNamespace(namespaces=("wp/v2", "yoast/v1")))
    values: dict[str, Any] = {}
    out = with_seo_page(ctx, sheet, values, {}, {CANONICAL: {"type": "string"}}, {})
    assert [p.key for p in out.pages] == ["general", "meta", "seo"]
    assert [f.key for f in out.pages[1].fields] == ["meta.other"]
    no_yoast = SimpleNamespace(info=SimpleNamespace(namespaces=("wp/v2",)))
    assert with_seo_page(no_yoast, sheet, values, {}, {}, {}) is sheet


def test_page_types_are_yoasts_twelve() -> None:
    assert len(PAGE_TYPES) == 12 and PAGE_TYPES[0][0] == "WebPage"


# -- WP-Cron beyond posts ---------------------------------------------------------------


class _Api:
    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.asked: list[tuple[str, dict[str, Any]]] = []

    def get(self, route: str, **params: Any) -> Any:
        self.asked.append((route, params))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_cron_events_opens_the_slug_wp_crontrol_registers() -> None:
    # WP Crontrol 2.0.0 on the test site: add_management_page(..., 'wp-crontrol', ...).
    assert CRON_EVENTS == "tools.php?page=wp-crontrol"


def test_crontrol_active_reads_only_the_plugin_list() -> None:
    api = _Api([{"plugin": "wp-crontrol/wp-crontrol", "status": "active"}])
    assert crontrol_active(api) is True
    assert api.asked == [("wp/v2/plugins", {"_fields": "plugin,status"})]
    assert (
        crontrol_active(_Api([{"plugin": "wp-crontrol/wp-crontrol", "status": "inactive"}]))
        is False
    )
    assert crontrol_active(_Api([])) is False
    assert crontrol_active(_Api(WordPressApiError("No.", status=403))) is None


def test_the_cron_row_says_only_posts_are_checked_and_opens_cron_events_when_active() -> None:
    active = cron_row("Radio", "https://radio.example/", True)
    assert active.link == f"https://radio.example/wp-admin/{CRON_EVENTS}"
    assert "Only scheduled posts and pages can be checked from here" in active.detail
    assert "Tools > Cron Events" in active.detail and "WP Crontrol" in active.detail
    off = cron_row("Radio", "https://radio.example", False)
    assert off.link == "" and "not active on Radio" in off.detail
    unknown = cron_row("Radio", "https://radio.example", None)
    assert unknown.link == "" and "could not read Radio's plugin list" in unknown.detail
    assert off.cell("state") == unknown.cell("state") == "not checked here"


def test_scheduled_tasks_claim_no_unrecorded_namespace() -> None:
    area = next(a for a in THIRD_SWEEP if a.area == "Scheduled tasks")
    assert area.namespaces == ()
    assert sweep_disposition(area, ("wp/v2",)).status == "covered"
