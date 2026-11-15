"""Packages 8 to 13, wx-free: WooCommerce, The Events Calendar, Yoast SEO and QAF on the site.

The fakes answer in the shapes the test site's public REST index publishes
(WooCommerce 11.2.2, The Events Calendar 6.18.3, Yoast SEO 28.8, the forms
plugin's baf/v1); nothing here reaches a network.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, timedelta, timezone
from typing import Any

import pytest

from quill.core.wordpress import workbench_events as ev
from quill.core.wordpress import workbench_forms_site as qaf
from quill.core.wordpress import workbench_seo as seo
from quill.core.wordpress import workbench_shop_catalog as cat
from quill.core.wordpress import workbench_shop_orders as orders
from quill.core.wordpress import workbench_shop_settings as shop_settings
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_events import EventDateError
from quill.core.wordpress.plugin_shop_seo import ShopValueError
from quill.core.wordpress.workbench_load import SiteContext, load

SITE = "Radio"

PRODUCT = {
    "id": 9,
    "name": "Mug",
    "type": "simple",
    "status": "publish",
    "sku": "MUG-1",
    "price": "10.00",
    "regular_price": "12.00",
    "sale_price": "10.00",
    "stock_status": "instock",
    "manage_stock": True,
    "stock_quantity": 4,
    "categories": [{"id": 3, "name": "Gifts"}],
    "tags": [],
    "catalog_visibility": "visible",
    "variations": [],
    "permalink": "https://radio.example/mug",
}
EVENT = {
    "id": 21,
    "title": "Open Day",
    "status": "publish",
    "start_date": "2026-11-21 10:00:00",
    "end_date": "2026-11-21 16:00:00",
    "utc_start_date": "2026-11-21 15:00:00",
    "timezone": "America/New_York",
    "timezone_abbr": "EST",
    "all_day": False,
    "venue": {"id": 5, "venue": "The Hall"},
    "organizer": [{"id": 6, "organizer": "Ann"}],
    "cost": "Free",
    "url": "https://radio.example/event/open-day/",
}


@dataclass
class _Info:
    namespaces: tuple[str, ...]


class PluginApi:
    """A site with WooCommerce, The Events Calendar and Yoast SEO."""

    def __init__(self) -> None:
        self.reads: list[tuple[str, dict[str, Any]]] = []

    def get(self, route: str, **params: Any) -> Any:
        self.reads.append((route, params))
        answers: dict[str, Any] = {
            "wc/v3/data/currencies/current": {"code": "USD"},
            "wc/v3/reports/sales": [
                {
                    "total_sales": "120.00",
                    "net_sales": "110.00",
                    "total_orders": 3,
                    "total_items": 5,
                    "total_refunds": "10.00",
                    "total_discount": "0.00",
                    "totals": {"2026-11-02": {"sales": "120.00", "orders": 3}},
                }
            ],
            "wc/v3/reports/top_sellers": [{"name": "Mug", "product_id": 9, "quantity": 4}],
            "wc/v3/reports/orders/totals": [
                {"slug": "processing", "name": "Processing", "total": 2},
                {"slug": "failed", "name": "Failed", "total": 0},
            ],
            "wc/v3/settings": [
                {"id": "general", "label": "General"},
                {"id": "advanced", "label": "Advanced"},
            ],
            "wc/v3/settings/general": [
                {
                    "id": "woocommerce_currency",
                    "label": "Currency",
                    "type": "select",
                    "value": "USD",
                    "options": {"USD": "United States (US) dollar", "EUR": "Euro"},
                },
                {
                    "id": "woocommerce_calc_taxes",
                    "label": "Enable taxes",
                    "type": "checkbox",
                    "value": "no",
                },
            ],
            "wc/v3/settings/advanced": [
                {"id": "woocommerce_api_key", "label": "Key", "type": "password", "value": "SECRET"}
            ],
            "tribe/events/v1/events": {"events": [EVENT], "total": 1, "total_pages": 1},
            "tribe/events/v1/venues": {
                "venues": [{"id": 5, "venue": "The Hall", "city": "Town", "phone": "555"}],
                "total_pages": 1,
            },
            "tribe/events/v1/organizers": {
                "organizers": [{"id": 6, "organizer": "Ann", "email": "ann@example.com"}],
                "total_pages": 1,
            },
            "yoast/v1/seo_scores": {
                "scores": [{"name": "good", "amount": 4}, {"name": "bad", "amount": 1}]
            },
        }
        if route.startswith("wc/v3/reports/") and route not in answers:
            raise WordPressApiError("Sorry, you cannot list resources.", status=403)
        if route == "yoast/v1/readability_scores":
            raise WordPressApiError("No.", status=403)
        return answers.get(route, [])

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        self.reads.append((route, dict(params or {})))
        if route == "wc/v3/products":
            yield PRODUCT
        elif route == "wc/v3/customers":
            yield {
                "id": 2,
                "first_name": "Ann",
                "last_name": "Lee",
                "username": "ann",
                "email": "ann@example.com",
                "billing": {"phone": "555", "address_1": "1 Main St"},
                "date_created_gmt": "2026-10-01T10:00:00",
                "is_paying_customer": True,
            }
        elif route == "wc/v3/coupons":
            yield {
                "id": 31,
                "code": "spring10",
                "discount_type": "percent",
                "amount": "10.00",
                "usage_count": 3,
                "usage_limit": 100,
                "date_expires": "2026-12-31T00:00:00",
            }
        elif route in ("wp/v2/posts", "wp/v2/pages"):
            yield {
                "id": 4 if route.endswith("posts") else 5,
                "type": "post" if route.endswith("posts") else "page",
                "title": {"raw": "Hello"},
                "link": "https://radio.example/hello/",
                "status": "publish",
                "meta": {
                    "_yoast_wpseo_title": "",
                    "_yoast_wpseo_metadesc": "Short",
                    "_yoast_wpseo_focuskw": "",
                },
                "yoast_head_json": {
                    "title": "Hello - " + "x" * 70,
                    "description": "Short",
                    "canonical": "https://radio.example/hello/",
                    "robots": {"index": "noindex"},
                },
            }


def _ctx(api: Any, *namespaces: str) -> SiteContext:
    ctx = SiteContext(SITE, api, url="https://radio.example")
    ctx.info = _Info(namespaces)  # type: ignore[assignment]
    return ctx


_ALL = ("wp/v2", "wc/v3", "tribe/events/v1", "yoast/v1")


# -- Package 8: the catalogue ----------------------------------------------------------


def test_a_filter_node_narrows_on_the_site_and_rows_carry_properties() -> None:
    api = PluginApi()
    rows = load(_ctx(api, *_ALL), "shop:products", {"stock_status": "outofstock"}, {"x": "1"})
    route, params = api.reads[0]
    assert route == "wc/v3/products" and params["stock_status"] == "outofstock"
    assert "x" not in params  # not a WooCommerce argument
    (row,) = rows
    assert row.raw["sku"] == "MUG-1" and row.raw["categories"] == "Gifts"
    assert row.raw["category_ids"] == [3] and "on sale from 12.00" in row.detail


def test_edit_product_sends_only_what_changed_and_previews_it() -> None:
    row = cat.product_row(PRODUCT, SITE)
    edit = cat.ProductEdit(
        regular_price="14.00", sale_price="", stock_quantity="4", status="draft",
        category_ids=(3,), category_names="Gifts",
    )  # fmt: skip
    body = cat.edit_body(row.raw, edit)
    assert body == {"regular_price": "14.00", "sale_price": "", "status": "draft"}
    lines = cat.edit_preview("Mug", SITE, row.raw, body, edit)
    assert "Regular price: 12.00 becomes 14.00." in lines
    assert any("the sale ends" in line for line in lines)
    with pytest.raises(ShopValueError, match="with no currency sign"):
        cat.edit_body(row.raw, cat.ProductEdit(regular_price="$14"))


def test_categories_are_matched_by_name_and_an_unknown_one_is_named() -> None:
    known = [{"id": 3, "name": "Gifts"}, {"id": 4, "name": "Mugs"}]
    assert cat.category_ids("mugs, Gifts", known) == ((4, 3), "Mugs, Gifts")
    with pytest.raises(ShopValueError, match="no category called Hats"):
        cat.category_ids("Hats", known)


def test_new_products_are_drafts_and_variations_are_lines() -> None:
    body = cat.new_product_body("Cap", "8")
    assert body["status"] == "draft" and body["type"] == "simple"
    assert "draft" in cat.new_product_preview(body, SITE)[1]
    lines = cat.variation_lines([
        {"id": 1, "attributes": [{"option": "Large"}], "price": "14", "stock_status": "instock",
         "sku": "L"},
    ])  # fmt: skip
    assert lines == ["Large: 14, in stock, SKU L"]


# -- Package 9: orders, refunds, coupons, customers, reports ----------------------------

ORDER = {
    "id": 77,
    "number": "1077",
    "status": "processing",
    "total": "24.00",
    "currency": "USD",
    "payment_method_title": "Stripe",
    "refunds": [{"id": 1, "total": "-4.00"}],
}


def test_a_status_change_says_which_email_it_sends() -> None:
    lines = orders.status_preview("1077", "processing", "completed", SITE)
    assert "processing becomes completed" in lines[0]
    assert "emails the customer that the order is complete" in lines[1]
    assert "no money moves" in orders.status_preview("1077", "processing", "refunded", SITE)[1]
    with pytest.raises(ShopValueError):
        orders.status_preview("1077", "processing", "shipped", SITE)


def test_a_refund_is_checked_warned_and_needs_the_amount_typed() -> None:
    assert str(orders.refunded_so_far(ORDER)) == "4.00"
    with pytest.raises(ShopValueError, match="Only 20.00 is left"):
        orders.plan_refund(ORDER, "25", "", through_gateway=True)
    with pytest.raises(ShopValueError):
        orders.plan_refund(ORDER, "0", "", through_gateway=True)
    plan = orders.plan_refund(ORDER, "12.5", "Broken", through_gateway=True)
    lines = orders.refund_preview(plan, SITE)
    assert lines[0].startswith("Money warning: this refunds 12.50 USD")
    assert "asks Stripe to return 12.50 USD" in lines[1] and "cannot be taken back" in lines[1]
    assert "7.50 USD" in lines[3]
    assert not orders.refund_confirmed(plan, None)
    assert not orders.refund_confirmed(plan, "12.5")
    assert orders.refund_confirmed(plan, " $12.50 ")
    assert orders.refund_body(plan) == {
        "amount": "12.50", "reason": "Broken", "api_refund": True, "api_restock": False,
    }  # fmt: skip
    record = orders.plan_refund(ORDER, "1", "", through_gateway=False)
    assert "no money is returned" in orders.refund_preview(record, SITE)[1]
    assert orders.NEVER_BATCHED == {"wordpress.workbench.refund_order"}


def test_notes_are_read_and_a_customer_note_says_it_is_emailed() -> None:
    lines = orders.note_lines([
        {"note": "Shipped", "customer_note": True, "date_created_gmt": "2026-11-02T10:00:00"},
        {"note": "<p>Called</p>", "customer_note": False, "author": "Jeff"},
    ])  # fmt: skip
    assert "to the customer: Shipped" in lines[0] and "private, by Jeff:" in lines[1]
    assert "emails it to them" in orders.note_preview("1077", "Hi", True, SITE)[1]
    with pytest.raises(ShopValueError):
        orders.note_preview("1077", " ", False, SITE)


def test_coupons_list_and_are_checked_before_sending() -> None:
    rows = load(_ctx(PluginApi(), *_ALL), "shop:coupons", {}, {})
    (row,) = rows
    assert row.cells == {
        "code": "spring10", "discount": "10.00 percent off", "used": "3 of 100",
        "expires": "2026-12-31",
    }  # fmt: skip
    spec = orders.CouponSpec("SPRING10", "percent", "15", "2026-12-31", "100")
    assert orders.coupon_body(spec, row.raw) == {"code": "SPRING10", "amount": "15"}
    for bad in (
        orders.CouponSpec("X", "percent", "150"),
        orders.CouponSpec("X", "fixed_cart", "5", "31/12/2026"),
        orders.CouponSpec("", "fixed_cart", "5"),
    ):
        with pytest.raises(ShopValueError):
            orders.coupon_body(bad)


def test_customers_keep_no_contact_details() -> None:
    (row,) = load(_ctx(PluginApi(), *_ALL), "shop:customers", {}, {})
    assert row.cells["name"] == "Ann Lee" and row.cells["paying"] == "yes"
    shown = repr(row.raw) + row.detail + repr(row.cells)
    assert "ann@example.com" not in shown and "555" not in shown and "Main St" not in shown


def test_reports_are_sentences_with_tables_and_a_refused_one_says_so() -> None:
    rows = load(_ctx(PluginApi(), *_ALL), "shop:reports", {}, {})
    said = {r.key: r.cell("says") for r in rows}
    assert said["sales"].startswith("This month, 3 orders and 5 items: 120.00 USD in sales")
    assert "2026-11-02: 3 orders" in rows[0].raw["table"]
    assert said["top_sellers"] == "Mug: 4 sold"
    assert said["orders_totals"] == "Processing: 2"
    assert said["products_totals"].startswith("not read:")


# -- Package 10: store settings ---------------------------------------------------------


def test_settings_are_read_in_words_and_a_password_is_never_kept() -> None:
    rows = load(_ctx(PluginApi(), *_ALL), "shop:settings", {}, {})
    by = {r.key: r for r in rows}
    assert by["general/woocommerce_currency"].cell("value") == "United States (US) dollar"
    assert by["general/woocommerce_calc_taxes"].cell("value") == "off"
    secret = by["advanced/woocommerce_api_key"]
    assert "SECRET" not in repr(secret.raw) + secret.detail + repr(secret.cells)
    with pytest.raises(ShopValueError, match="password-style"):
        shop_settings.choices_for(secret.raw)
    currency = by["general/woocommerce_currency"].raw
    assert shop_settings.choices_for(currency).values[1] == ("EUR", "Euro")
    lines = shop_settings.setting_preview(currency, "EUR", SITE)
    assert "United States (US) dollar becomes Euro" in lines[0]
    assert shop_settings.setting_route(currency) == "wc/v3/settings/general/woocommerce_currency"
    with pytest.raises(ShopValueError):
        shop_settings.value_to_send({"type": "number", "label": "Days"}, "ten")


# -- Package 11: The Events Calendar ------------------------------------------------------


def test_events_say_their_zone_and_your_clock_and_past_is_newest_first() -> None:
    api = PluginApi()
    ctx = _ctx(api, *_ALL)
    (row,) = load(ctx, "events:upcoming", {}, {})
    assert api.reads[0][1]["start_date"] == "now"
    assert row.cell("when") == "Saturday 21 November 2026, 10:00 to 16:00"
    assert "America/New_York (EST)" in row.detail and row.cell("venue") == "The Hall"
    assert row.raw["venue_id"] == 5 and row.subkind == "events_calendar"
    london = ev.event_row(EVENT, SITE, local=UTC)
    assert "starts Saturday 21 November 2026 at 15:00" in london.detail
    load(ctx, "events:past", {}, {})
    assert api.reads[-1][1]["ends_before"] == "now"
    assert ev.event_row(EVENT, SITE, local=timezone(timedelta(hours=-5))).raw["your_time"]


def test_venues_and_organizers_list_and_a_site_without_the_plugin_says_so() -> None:
    api = PluginApi()
    (venue,) = load(_ctx(api, *_ALL), "events:venues", {}, {})
    assert venue.cells == {"name": "The Hall", "where": "Town", "phone": "555"}
    (organizer,) = load(_ctx(api, *_ALL), "events:organizers", {}, {})
    assert organizer.raw["email"] == "ann@example.com"
    with pytest.raises(WordPressApiError, match="does not list The Events Calendar"):
        load(_ctx(PluginApi(), "wp/v2"), "events:upcoming", {}, {})


def test_a_recurring_occurrence_is_said_honestly() -> None:
    row = ev.event_row({**EVENT, "recurring": True}, SITE)
    assert row.subkind == "recurring" and "Events Calendar Pro" in row.detail
    with pytest.raises(WordPressApiError, match="not here"):
        ev.require_not_recurring(row)
    assert ev.recurring_words(EVENT) == ""


def test_event_bodies_are_checked_drafts_and_edits_send_changes() -> None:
    spec = ev.EventSpec("Open Day", "2026-11-21 10:00", "2026-11-21 16:00", venue_id=5)
    body = ev.event_body(spec)
    assert body["status"] == "draft" and body["start_date"] == "2026-11-21 10:00:00"
    assert "timezone" not in body  # the site's own zone
    assert "Times are in the site's own time zone." in ev.event_preview(
        spec, body, SITE, venue="The Hall", new=True
    )
    old = ev.event_row(EVENT, SITE).raw
    moved = ev.EventSpec(
        "Open Day", "2026-11-21 11:00", "2026-11-21 16:00", timezone="America/New_York",
        venue_id=5, cost="Free",
    )  # fmt: skip
    assert ev.event_body(moved, old) == {"start_date": "2026-11-21 11:00:00"}
    with pytest.raises(EventDateError, match="ends before it starts"):
        ev.event_body(ev.EventSpec("X", "2026-11-21 16:00", "2026-11-21 10:00"))
    assert ev.between_params("2026-11-01", "2026-11-30") == {
        "start_date": "2026-11-01 00:00:00", "end_date": "2026-11-30 23:59:59",
    }  # fmt: skip
    assert ev.venue_body(ev.VenueSpec("Hall", {"city": "Town", "zip": ""})) == {
        "venue": "Hall", "city": "Town",
    }  # fmt: skip


# -- Package 12: Yoast SEO --------------------------------------------------------------


def test_seo_rows_read_the_head_and_meta_and_say_what_to_look_at() -> None:
    api = PluginApi()
    rows = load(_ctx(api, *_ALL), "seo:items", {}, {})
    assert [r.raw["route"] for r in rows] == ["wp/v2/posts/4", "wp/v2/pages/5"]
    assert api.reads[0][1]["context"] == "edit"
    row = rows[0]
    assert row.cell("index") == "not indexed" and row.cell("keyphrase") == "not set"
    assert "title over 60 characters" in row.detail and "no focus keyphrase" in row.detail
    assert "(cut off after 60 characters)" in row.raw["appearance"]
    with pytest.raises(WordPressApiError, match="does not list Yoast SEO"):
        load(_ctx(api, "wp/v2"), "seo:items", {}, {})


def test_edit_seo_writes_only_registered_meta_and_names_the_rest() -> None:
    meta = {"_yoast_wpseo_title": "", "_yoast_wpseo_metadesc": "Short"}
    body, unwritable = seo.seo_body(meta, seo.SeoEdit("New title", "Short", "radio", "1"))
    assert body == {"_yoast_wpseo_title": "New title"}
    assert unwritable == ["Focus keyphrase", "Show in search results"]
    lines = seo.seo_preview("Hello", SITE, meta, body, unwritable)
    assert "SEO title: not set becomes New title." in lines
    assert any("Yoast panel in wp-admin" in line for line in lines)


def test_site_seo_gives_scores_in_words_and_the_wp_admin_only_jobs() -> None:
    rows = load(_ctx(PluginApi(), *_ALL), "seo:site", {}, {})
    scores = [r for r in rows if r.kind == "seo_score"]
    assert scores[0].cell("says") == "4 good, 1 needs improvement"
    assert scores[-1].cell("says").startswith("not read:")
    admin = [r for r in rows if r.kind == "dashboard"]
    assert len(admin) == len(seo.WP_ADMIN_ONLY)
    assert all(
        r.link.startswith("https://radio.example/wp-admin/admin.php?page=wpseo") for r in admin
    )


# -- Package 13: QAF on the site ----------------------------------------------------------


def test_qaf_form_status_delete_and_settings_words() -> None:
    assert "can no longer send" in qaf.status_preview("Signup", "active", "inactive", SITE)[1]
    with pytest.raises(WordPressApiError):
        qaf.status_preview("Signup", "active", "archived", SITE)
    lines = qaf.delete_preview("Signup", 3, SITE)
    assert "for good" in lines[0] and "3 responses" in lines[1] and "Signup, exactly" in lines[3]
    settings = {"ajax_submission": True, "rate_limit_count": 10, "conditional_logic": []}
    assert qaf.setting_lines(settings) == [("ajax_submission", "on"), ("rate_limit_count", "10")]
    assert qaf.setting_value(True, "off") is False and qaf.setting_value(10, "12") == 12
    with pytest.raises(WordPressApiError):
        qaf.setting_value(10, "many")
    body = qaf.settings_body(settings, "rate_limit_count", 12)
    assert body == {"settings": {**settings, "rate_limit_count": 12}}


def test_a_qaf_flag_sends_only_that_flag() -> None:
    class Api:
        def __init__(self) -> None:
            self.posts: list[tuple[str, Any]] = []

        def get(self, route: str, **_p: Any) -> Any:
            return {"id": 8, "is_starred": False, "fields": {"name": "Ann"}}

        def post(self, route: str, body: Any = None, **_p: Any) -> Any:
            self.posts.append((route, body))
            return {}

    api = Api()
    assert qaf.set_entry_flag(api, "baf/v1/entries/8", "is_starred", True) is False
    assert api.posts == [("baf/v1/entries/8", {"is_starred": True})]
    assert qaf.view_lines(
        [{"title": "Map", "form_id": 2, "view_type": "map"}], {"2": "Signup"}
    ) == ["Map: map view of Signup, draft"]


# -- every command: help, and a key or its reason ---------------------------------------


def test_every_new_command_has_help_and_a_key_or_a_reason() -> None:
    from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, WORDPRESS_KEYS
    from quill.core.wordpress.workbench_plugin_actions import (
        KEYLESS,
        PLUGIN_ACTION_ROWS,
        QAF_FORM_ROWS,
    )
    from quill.core.workbench.actions import Tier

    owned = set(KEYLESS)
    rows = [r for rows in PLUGIN_ACTION_ROWS.values() for r in rows] + list(QAF_FORM_ROWS)
    for row in rows:
        assert row.help, row.command_id
        if row.command_id in owned or row.command_id in WORDPRESS_KEYS:
            continue
        assert row.command_id.rsplit(".", 1)[1] in (
            "read", "sheet", "open_on_site", "copy_link",
        ), row.command_id  # fmt: skip
    refund = next(r for r in WORDPRESS_ACTIONS.rows_for("shop_order") if "refund" in r.command_id)
    assert refund.tier is Tier.DESTRUCTIVE


def test_new_nodes_and_kinds_have_f1_help() -> None:
    from quill.core.wordpress.workbench_node_help import ROW_HELP, node_help
    from quill.core.wordpress.workbench_plugin_nodes import PLUGIN_NODES

    for node in PLUGIN_NODES:
        assert node_help(node.key), node.key
        assert node.row_type in ROW_HELP, node.row_type
    assert "refund" in ROW_HELP["shop_order"]


# -- the Forms key (wordpress.md 19, "a key for the Forms commands") ----------------------


def test_responses_has_f_on_the_wordpress_layer_in_both_editors() -> None:
    from quill.core.forms import menu as forms_menu
    from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
    from quill.core.wordpress import keys
    from quill.core.wordpress.menu import LAYER_KEYS

    chord = "Ctrl+Alt+Shift+Grave, F"
    assert "F" not in LAYER_KEYS  # free on the layer
    assert [c for c, k in DEFAULT_KEYMAP.items() if k == chord] == ["forms.responses"]
    assert chord not in DEFAULT_ALIASES.values()
    layer = keys.WordPressKeyLayer()
    layer.start()
    outcome = layer.press("F", keys.layer_from_bindings(DEFAULT_KEYMAP))
    assert outcome.command == "forms.responses"
    lite = {row[3]: row[2] for row in forms_menu.lite_rows("tools")}
    assert lite["cmd_forms_responses"] == chord
    assert all(not key for handler, key in lite.items() if handler != "cmd_forms_responses")
