"""Plugins QUILL recognises: events, products, SEO, and shop orders (9.15)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui import wordpress_plugin_dialogs as pdlg
from quill.ui.wordpress_plugin_commands import WordPressPluginCommands
from quill.ui.wordpress_shop_commands import WordPressShopCommands

API = "/wp-json/wp/v2"
TEC = "/wp-json/tribe/events/v1"
WC = "/wp-json/wc/v3"
MIXINS = (WordPressPluginCommands, WordPressShopCommands)

EDITOR = {
    "id": 1,
    "name": "Jeff",
    "roles": ["editor"],
    "capabilities": {"edit_posts": True, "manage_woocommerce": True},
}
AUTHOR = {"id": 9, "name": "Ann", "roles": ["author"], "capabilities": {}}

EVENT = {
    "id": 40,
    "title": "Open Day",
    "start_date": "2026-11-21 10:00:00",
    "end_date": "2026-11-21 16:00:00",
    "venue": {"id": 3, "venue": "Village Hall"},
    "url": "https://radio.example/event/open-day/",
}


@pytest.fixture
def site(wp: Any) -> Any:
    extra = tuple(m for m in MIXINS if not issubclass(type(wp), m))
    if extra:
        wp.__class__ = type("Wired", (type(wp), *extra), {})
    return wp


class _Script(list):
    def __init__(self) -> None:
        super().__init__()
        self.asked: list[dict[str, Any]] = []


@pytest.fixture
def fields(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Scripted Plugin Fields: append a dict (or a callable of the kwargs) per call."""
    script = _Script()
    asked = script.asked

    def answer(*_a: Any, **kwargs: Any) -> Any:
        asked.append(kwargs)
        if not script:
            return None
        value = script.pop(0)
        return value(**kwargs) if callable(value) else value

    monkeypatch.setattr(pdlg, "ask_plugin_fields", answer)
    return script


def _index(wp_site: Any, namespaces: list[str], account: Any = EDITOR) -> None:
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2", *namespaces], "routes": {}})
    wp_site.on("GET", f"{API}/users/me", account)


def _open(site: Any, kind: str, remote_id: int = 40) -> lc.WorkingCopy:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind=kind,
        local_id=lc.new_local_id(),
        remote_id=remote_id,
        title="Item",
        text="x",
    )
    site.host.open_path(site.local.write_document(copy))
    return copy


# --------------------------------------------------------------------------- #
# Coming Up and New Event


def test_coming_up_without_the_events_calendar_says_why(site, wp_site, wp_dialogs):
    _index(wp_site, [])
    site.cmd_events_coming_up()
    assert "does not have The Events Calendar" in site.host.said
    assert not wp_dialogs.list_windows


def test_coming_up_lists_events_in_words_and_opens_one(site, wp_site, wp_dialogs):
    _index(wp_site, ["tribe/events/v1"])
    wp_site.on("GET", f"{TEC}/events", {"events": [EVENT]})
    wp_site.on(
        "GET",
        f"{API}/tribe_events/40",
        {"id": 40, "type": "tribe_events", "title": {"raw": "Open Day"}, "content": {"raw": ""}},
    )
    site.cmd_events_coming_up()
    assert "start_date=now" in wp_site.sent("GET", f"{TEC}/events")[0].full_url
    assert wp_dialogs.window["rows"] == [
        "Open Day, Saturday 21 November 2026, 10:00 to 16:00, at Village Hall"
    ]
    wp_dialogs.press("Open on &Site")
    assert site.host.browsed == [EVENT["url"]]
    wp_dialogs.enter(0)
    assert wp_site.sent("GET", f"{API}/tribe_events/40")


def test_nothing_coming_up_is_said(site, wp_site, wp_dialogs):
    _index(wp_site, ["tribe/events/v1"])
    wp_site.on("GET", f"{TEC}/events", {"events": []})
    site.cmd_events_coming_up()
    assert "Nothing is coming up on Community Radio." in site.host.said


@pytest.fixture
def form(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    script: list[Any] = []
    monkeypatch.setattr(bdlg, "ask_fields", lambda *_a, **_k: script.pop(0) if script else None)
    return script


def test_new_event_makes_a_draft_and_opens_it(site, wp_site, wp_dialogs, form):
    _index(wp_site, ["tribe/events/v1"])
    wp_site.on("GET", f"{TEC}/venues", {"venues": [{"id": 3, "venue": "Village Hall"}]})
    wp_site.on("POST", f"{TEC}/events", EVENT)
    wp_site.on(
        "GET",
        f"{API}/tribe_events/40",
        {"id": 40, "type": "tribe_events", "title": {"raw": "Open Day"}, "content": {"raw": ""}},
    )
    form.append({
        "title": "Open Day",
        "start": "2026-11-21 10:00",
        "end": "2026-11-21 16:00",
        "venue": 3,
    })
    site.cmd_new_event()
    body = wp_site.body(wp_site.sent("POST", f"{TEC}/events")[0])
    assert body == {
        "title": "Open Day",
        "start_date": "2026-11-21 10:00:00",
        "end_date": "2026-11-21 16:00:00",
        "status": "draft",
        "venue": 3,
    }
    assert "Event Open Day made as a draft on Community Radio." in site.host.said
    assert wp_site.sent("GET", f"{API}/tribe_events/40")


def test_new_event_refuses_a_date_it_cannot_read(site, wp_site, wp_dialogs, form):
    _index(wp_site, ["tribe/events/v1"])
    form.append({"title": "Open Day", "start": "next Saturday", "end": "", "venue": 0})
    site.cmd_new_event()
    assert "such as 2026-11-21 10:00. Nothing was made." in site.host.said
    assert not wp_site.sent("POST", f"{TEC}/events")


def test_new_event_that_ends_before_it_starts_is_refused(site, wp_site, wp_dialogs, form):
    _index(wp_site, ["tribe/events/v1"])
    form.append({
        "title": "Open Day",
        "start": "2026-11-21 10:00",
        "end": "2026-11-20 10:00",
        "venue": 0,
    })
    site.cmd_new_event()
    assert "ends before it starts" in site.host.said


def test_new_event_needs_a_name(site, wp_site, wp_dialogs, form):
    _index(wp_site, ["tribe/events/v1"])
    form.append({"title": " ", "start": "2026-11-21", "end": "", "venue": 0})
    site.cmd_new_event()
    assert "An event needs a name." in site.host.said


def test_new_event_needs_a_role_that_can_write(site, wp_site, wp_dialogs, form):
    _index(wp_site, ["tribe/events/v1"], account=AUTHOR)
    site.cmd_new_event()
    assert "which cannot add events" in site.host.said


def test_new_event_cancelled_makes_nothing(site, wp_site, wp_dialogs, form):
    _index(wp_site, ["tribe/events/v1"])
    site.cmd_new_event()
    assert not wp_site.sent("POST", f"{TEC}/events")


# --------------------------------------------------------------------------- #
# Properties and Plugin Fields


def test_properties_shows_an_events_dates_and_venue(site, wp_site, wp_dialogs):
    _open(site, "tribe_events")
    _index(wp_site, ["tribe/events/v1"])
    wp_site.on("GET", f"{TEC}/events/40", EVENT)
    site.cmd_properties()
    facts = wp_dialogs.asked("ask_properties")[0]["facts"]
    assert "Event starts: Saturday 21 November 2026 at 10:00" in facts
    assert "Venue: Village Hall" in facts
    assert "Plugin Fields" in facts


def test_properties_shows_price_stock_and_seo_lengths(site, wp_site, wp_dialogs):
    _open(site, "product")
    _index(wp_site, ["wc/v3", "yoast/v1"])
    wp_site.on(
        "GET",
        f"{WC}/products/40",
        {
            "id": 40,
            "name": "Mug",
            "price": "8",
            "regular_price": "10",
            "sale_price": "8",
            "stock_status": "instock",
            "manage_stock": True,
            "stock_quantity": 4,
        },
    )
    wp_site.on("GET", f"{API}/product/40", {"meta": {"_yoast_wpseo_title": "x" * 70}})
    site.cmd_properties()
    facts = wp_dialogs.asked("ask_properties")[0]["facts"]
    assert "Price: 8 (on sale from 10)" in facts
    assert "Stock: in stock, 4 left" in facts
    assert "SEO title: 70 characters, 10 over about 60" in facts


def test_properties_of_a_local_draft_reads_nothing_extra(site, wp_site, wp_dialogs):
    _open(site, "page", remote_id=0)
    site.cmd_properties()
    assert wp_dialogs.asked("ask_properties")
    assert not wp_site.requests


def test_properties_still_opens_when_the_index_is_refused(site, wp_site, wp_dialogs):
    _open(site, "page")
    site.cmd_properties()
    assert "Plugin Fields" not in wp_dialogs.asked("ask_properties")[0]["facts"]


def test_plugin_fields_needs_the_item_on_the_site(site, wp_site, fields):
    _open(site, "tribe_events", remote_id=0)
    site.cmd_plugin_fields()
    assert "Save Draft to Site first" in site.host.said


def test_plugin_fields_says_when_the_plugins_add_nothing(site, wp_site, fields):
    _open(site, "page")
    _index(wp_site, [])
    site.cmd_plugin_fields()
    assert "plugins add no fields to this page" in site.host.said


def test_plugin_fields_saves_event_dates_and_seo_meta(site, wp_site, fields):
    _open(site, "tribe_events")
    _index(wp_site, ["tribe/events/v1", "rankmath/v1"])
    wp_site.on("GET", f"{TEC}/events/40", EVENT)
    wp_site.on("GET", f"{TEC}/venues", {"venues": [{"id": 3, "venue": "Village Hall"}]})
    wp_site.on(
        "GET",
        f"{API}/tribe_events/40",
        {"meta": {"rank_math_title": "Old", "rank_math_description": ""}},
    )
    wp_site.on("POST", f"{TEC}/events/40", EVENT)
    wp_site.on("POST", f"{API}/tribe_events/40", {"id": 40})
    fields.append({
        "start": "2026-11-22 09:30",
        "end": "2026-11-22 12:00",
        "venue": 3,
        "rank_math_title": "Open Day at the Hall",
        "rank_math_description": "",
    })
    site.cmd_plugin_fields()
    asked = fields.asked[0]  # type: ignore[attr-defined]
    assert [f.label for f in asked["fields"]] == [
        "&Starts:",
        "&Ends:",
        "&Venue:",
        "SEO &title:",
        "SEO &description:",
    ]
    assert asked["limits"] == {"rank_math_title": 60, "rank_math_description": 160}
    event = wp_site.body(wp_site.sent("POST", f"{TEC}/events/40")[0])
    assert event == {
        "start_date": "2026-11-22 09:30:00",
        "end_date": "2026-11-22 12:00:00",
        "venue": 3,
    }
    meta = wp_site.body(wp_site.sent("POST", f"{API}/tribe_events/40")[0])
    assert meta == {"meta": {"rank_math_title": "Open Day at the Hall"}}
    assert (
        "Saved to Community Radio: the event's dates and venue, the SEO fields." in site.host.said
    )


def test_plugin_fields_refuses_an_end_before_the_start(site, wp_site, fields):
    _open(site, "tribe_events")
    _index(wp_site, ["tribe/events/v1"])
    wp_site.on("GET", f"{TEC}/events/40", EVENT)
    fields.append({"start": "2026-11-22 09:30", "end": "2026-11-21 12:00", "venue": 0})
    site.cmd_plugin_fields()
    assert "ends before it starts. Nothing was saved." in site.host.said


def _product(wp_site: Any) -> None:
    _index(wp_site, ["wc/v3"])
    wp_site.on(
        "GET",
        f"{WC}/products/40",
        {
            "id": 40,
            "name": "Mug",
            "price": "10",
            "regular_price": "10",
            "sale_price": "",
            "stock_status": "instock",
            "manage_stock": True,
            "stock_quantity": 4,
        },
    )
    wp_site.on("POST", f"{WC}/products/40", {"id": 40})


def test_a_price_change_is_confirmed_by_name_then_sent(site, wp_site, wp_dialogs, fields):
    _open(site, "product")
    _product(wp_site)
    wp_dialogs.answer("confirm", True)
    fields.append({"regular_price": "12.50", "sale_price": "", "stock": "6"})
    site.cmd_plugin_fields()
    assert (
        "Change the price of Mug on Community Radio?" in wp_dialogs.asked("confirm")[0]["message"]
    )
    body = wp_site.body(wp_site.sent("POST", f"{WC}/products/40")[0])
    assert body == {"regular_price": "12.50", "sale_price": "", "stock_quantity": 6}


def test_a_declined_price_change_sends_nothing(site, wp_site, wp_dialogs, fields):
    _open(site, "product")
    _product(wp_site)
    fields.append({"regular_price": "12.50", "sale_price": "", "stock": "4"})
    site.cmd_plugin_fields()
    assert not wp_site.sent("POST", f"{WC}/products/40")


def test_a_bad_price_or_stock_is_refused(site, wp_site, fields):
    _open(site, "product")
    _product(wp_site)
    fields.append({"regular_price": "£12", "sale_price": "", "stock": "4"})
    site.cmd_plugin_fields()
    assert "with no currency sign. Nothing was saved." in site.host.said
    fields.append({"regular_price": "10", "sale_price": "", "stock": "lots"})
    site.cmd_plugin_fields()
    assert "Stock needs a whole number" in site.host.said
    assert not wp_site.sent("POST", f"{WC}/products/40")


def test_plugin_fields_cancelled_sends_nothing(site, wp_site, fields):
    _open(site, "product")
    _product(wp_site)
    site.cmd_plugin_fields()
    assert not wp_site.sent("POST", f"{WC}/products/40")


# --------------------------------------------------------------------------- #
# Shop Orders


ORDER = {
    "id": 1042,
    "number": "1042",
    "status": "processing",
    "total": "45.00",
    "currency": "GBP",
    "date_created_gmt": "2026-11-03T16:12:00",
    "billing": {"first_name": "Sam", "last_name": "Smith"},
    "shipping": {"address_1": "1 High Street", "city": "Leeds"},
    "line_items": [{"name": "Mug", "quantity": 3, "total": "30.00"}],
}


def test_shop_orders_without_woocommerce_say_why(site, wp_site, wp_dialogs):
    _index(wp_site, [])
    site.cmd_shop_orders()
    assert "does not have WooCommerce" in site.host.said


def test_shop_orders_need_a_shop_role(site, wp_site, wp_dialogs):
    _index(wp_site, ["wc/v3"], account=AUTHOR)
    site.cmd_shop_orders()
    assert "cannot read the shop's orders" in site.host.said


def test_shop_orders_read_aloud_and_copy_only_after_asking(site, wp_site, wp_dialogs):
    _index(wp_site, ["wc/v3"])
    wp_site.on("GET", f"{WC}/orders", [ORDER])
    site.cmd_shop_orders()
    row = wp_dialogs.window["rows"][0]
    assert row.startswith("Order 1042, processing, 3 items, 45.00 GBP, from Sam Smith")
    assert "Ship to: 1 High Street, Leeds" in wp_dialogs.window["details"](0)
    wp_dialogs.press("&Copy Order...")
    assert site.host.clipboard == ""
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Copy Order...")
    assert "Sam Smith" in site.host.clipboard
    assert "Order 1042 copied." in site.host.said
    assert [r.get_method() for r in wp_site.requests if "/wc/v3/" in r.full_url] == ["GET"]


def test_no_orders_is_said(site, wp_site, wp_dialogs):
    _index(wp_site, ["wc/v3"])
    wp_site.on("GET", f"{WC}/orders", [])
    site.cmd_shop_orders()
    assert "has no orders yet" in site.host.said


# --------------------------------------------------------------------------- #
# the Plugin Fields window


def test_the_fields_window_counts_and_says_when_a_field_goes_over(wx_session_app) -> None:
    import wx

    from quill.core.wordpress.block_catalog import Field

    frame = wx.Frame(None)
    said: list[str] = []
    seen: list[Any] = []

    def show_modal(dialog: Any, _label: str) -> int:
        edit = dialog.controls[1]
        edit.ChangeValue("x" * 61)
        dialog._count("t", edit, dialog.counts["t"], "SEO title", 60)
        seen.append(dialog.counts["t"].GetValue())
        edit.ChangeValue("short")
        dialog._count("t", edit, dialog.counts["t"], "SEO title", 60)
        return wx.ID_OK

    try:
        answers = pdlg.ask_plugin_fields(
            frame,
            show_modal,
            title="Plugin Fields",
            purpose="Test.",
            fields=[
                Field("venue", "&Venue:", "choice", "Where.", 3, ["None", "Hall"], [0, 3]),
                Field("t", "SEO &title:", "text", "Title.", "Old"),
            ],
            limits={"t": 60},
            announce=said.append,
        )
    finally:
        frame.Destroy()
    assert answers == {"venue": 3, "t": "short"}
    assert seen == ["SEO title: 61 characters, 1 over about 60"]
    assert said == [
        "SEO title is now over 60 characters.",
        "SEO title is back within 60 characters.",
    ]
