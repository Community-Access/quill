"""Packages 8 to 13 in the Workbench window: every new command, called, over a fake site.

The real provider and frame; the site is a fake that answers in the shapes the
test site's REST index publishes, the dialogs answer from queues, and
background work runs inline. Each change is previewed before anything is
sent, and a declined preview sends nothing.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_events import event_row, organizer_row, venue_row  # noqa: E402
from quill.core.wordpress.workbench_permissions import Access  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.wordpress.workbench_seo import seo_row  # noqa: E402
from quill.core.wordpress.workbench_shop_catalog import product_row  # noqa: E402
from quill.core.wordpress.workbench_shop_orders import coupon_row  # noqa: E402
from quill.core.wordpress.workbench_shop_settings import setting_row  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"
ORDER = {
    "id": 77,
    "number": "1077",
    "status": "processing",
    "total": "24.00",
    "currency": "USD",
    "payment_method_title": "Stripe",
    "refunds": [],
}
EVENT = {
    "id": 21,
    "title": "Open Day",
    "start_date": "2026-11-21 10:00:00",
    "end_date": "2026-11-21 16:00:00",
    "timezone": "America/New_York",
    "venue": {"id": 5, "venue": "The Hall"},
}


class FakeApi:
    def __init__(self) -> None:
        self.site_name = SITE
        self.sent: list[tuple[str, str, Any]] = []

    def get(self, route: str, **_p: Any) -> Any:
        if route == "wp/v2/users/me":
            caps = {"manage_options": True, "edit_posts": True}
            return {"id": 1, "name": "Jeff", "roles": ["administrator"], "capabilities": caps}
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", "wc/v3", "tribe/events/v1", "yoast/v1"]}
        answers: dict[str, Any] = {
            "wc/v3/products/categories": [{"id": 3, "name": "Gifts"}, {"id": 4, "name": "Mugs"}],
            "wc/v3/orders/77": ORDER,
            "wc/v3/orders/77/notes": [{"note": "Paid", "customer_note": False}],
            "tribe/events/v1/venues": {
                "venues": [{"id": 5, "venue": "The Hall"}],
                "total_pages": 1,
            },
            "tribe/events/v1/events": {"events": [EVENT], "total_pages": 1},
            "baf/v1/forms/2": {
                "id": 2,
                "settings": {"ajax_submission": True, "rate_limit_count": 10},
            },
            "baf/v1/views": [{"title": "Map", "form_id": 2, "view_type": "map"}],
            "baf/v1/entries/8": {"id": 8, "is_starred": False},
        }
        return answers.get(route, [])

    def iter_collection(self, route: str, *_a: Any, **_k: Any):
        if route.endswith("/variations"):
            yield {
                "id": 1,
                "attributes": [{"option": "Large"}],
                "price": "14",
                "stock_status": "instock",
            }
        if route == "baf/v1/entries":
            yield {"id": 8, "created_at": "2026-11-02", "fields": {"name": "Ann"}}

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.sent.append(("POST", route, body))
        return {}

    def delete(self, route: str, **_p: Any) -> Any:
        self.sent.append(("DELETE", route, None))
        return {}


class _Host:
    def __init__(self, said: list[str]) -> None:
        self.said = said
        self.parent = None

    def announce(self, text: str) -> None:
        self.said.append(text)

    def open_in_browser(self, url: str) -> None:
        pass


class _Commands:
    def __init__(self, said: list[str]) -> None:
        self.host = _Host(said)

    def sites(self) -> SiteStore:
        return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


class Answers:
    """Queues the dialogs answer from; what each was shown is kept."""

    def __init__(self) -> None:
        self.texts: list[str | None] = []
        self.choices: list[int | None] = []
        self.previews: list[dict[str, Any]] = []
        self.reports: list[dict[str, Any]] = []
        self.yes = True


@pytest.fixture
def bench(wx_session_app, tmp_path, monkeypatch):
    tx.clear_cache()
    said: list[str] = []
    api = FakeApi()
    answers = Answers()
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: answers.texts.pop(0))
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: answers.choices.pop(0))
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: answers.reports.append(k))
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: answers.previews.append(k) or answers.yes
    )
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said, frame.api, frame.answers = said, api, answers  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _ref(key: str) -> NodeRef:
    return NodeRef("site", key, SITE)


def _product() -> WbRow:
    return product_row(
        {"id": 9, "name": "Mug", "status": "publish", "regular_price": "12.00",
         "categories": [{"id": 3, "name": "Gifts"}], "manage_stock": True, "stock_quantity": 4},
        SITE,
    )  # fmt: skip


def _order() -> WbRow:
    return WbRow("shop_order", SITE, "77", {"what": "Shop order 1077"}, "", status="processing",
                 raw={"order": "1077"})  # fmt: skip


# -- Package 8 ---------------------------------------------------------------------------


def test_edit_product_previews_then_sends_only_the_changes(bench) -> None:
    a = bench.answers
    a.texts += ["14.00", "", "4", "Mugs"]
    a.choices += [0]  # published, as it is
    bench.provider.do_edit_product(_ref("shop"), _product())
    assert "Regular price: 12.00 becomes 14.00." in a.previews[0]["lines"]
    assert bench.api.sent == [
        ("POST", "wc/v3/products/9", {"regular_price": "14.00", "categories": [{"id": 4}]})
    ]


def test_a_declined_preview_sends_nothing(bench) -> None:
    a = bench.answers
    a.yes = False
    bench.provider.do_duplicate_product(_ref("shop"), _product())
    bench.provider.do_trash_product(_ref("shop"), _product())
    assert len(a.previews) == 2 and bench.api.sent == []


def test_new_duplicate_trash_and_variations(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Cap", "8"]
    bench.provider.do_new_product(_ref("shop"), None)
    bench.provider.do_duplicate_product(_ref("shop"), _product())
    bench.provider.do_trash_product(_ref("shop"), _product())
    bench.provider.do_show_variations(_ref("shop"), _product())
    assert [(m, r) for m, r, _b in api.sent] == [
        ("POST", "wc/v3/products"),
        ("POST", "wc/v3/products/9/duplicate"),
        ("DELETE", "wc/v3/products/9"),
    ]
    assert api.sent[0][2]["status"] == "draft"
    assert a.reports[-1]["text"] == "Large: 14, in stock"


def test_ctrl_n_and_delete_reach_the_plugin_commands(bench) -> None:
    a = bench.answers
    a.texts += ["Cap", "8"]
    bench.provider.do_new_here(_ref("shop_out_of_stock"), None)
    bench.provider.do_trash(_ref("shop"), _product())
    assert [r for _m, r, _b in bench.api.sent] == ["wc/v3/products", "wc/v3/products/9"]


# -- Package 9 ---------------------------------------------------------------------------


def test_change_status_previews_the_email(bench) -> None:
    a = bench.answers
    a.choices += [2]  # pending, processing (skipped), on-hold, completed...
    bench.provider.do_change_order_status(_ref("shop_orders"), _order())
    assert "emails the customer that the order is complete" in a.previews[0]["lines"][1]
    assert bench.api.sent == [("POST", "wc/v3/orders/77", {"status": "completed"})]


def test_order_notes_read_then_add_one_to_the_customer(bench) -> None:
    a = bench.answers
    a.choices += [2]  # the one note, then Add a private, then Add to the customer
    a.texts += ["Shipped today"]
    bench.provider.do_order_notes(_ref("shop_orders"), _order())
    assert bench.api.sent == [
        ("POST", "wc/v3/orders/77/notes", {"note": "Shipped today", "customer_note": True})
    ]
    assert "emailed it to the customer" in bench.said[-1]


def test_a_refund_needs_the_amount_typed_and_says_how_money_moved(bench) -> None:
    a = bench.answers
    a.texts += ["10", "Broken", "10"]  # amount, reason, then the wrong confirmation
    a.choices += [0]
    bench.provider.do_refund_order(_ref("shop_orders"), _order())
    assert a.previews[0]["lines"][0].startswith("Money warning")
    assert bench.api.sent == [] and "did not match" in bench.said[-1]
    a.texts += ["10", "Broken", "10.00"]
    a.choices += [1]  # record only
    bench.provider.do_refund_order(_ref("shop_orders"), _order())
    assert bench.api.sent == [
        ("POST", "wc/v3/orders/77/refunds",
         {"amount": "10.00", "reason": "Broken", "api_refund": False, "api_restock": False}),
    ]  # fmt: skip
    assert bench.said[-1].endswith("as a record only.")


def test_a_refund_is_never_for_a_selection(bench, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "selected_rows", lambda: [_order(), _order()])
    bench.provider.do_refund_order(_ref("shop_orders"), _order())
    assert bench.answers.previews == [] and "one order at a time" in bench.said[-1]


def test_coupons_new_edit_and_trash(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["SPRING10", "10", "", ""]
    a.choices += [0]
    bench.provider.do_new_here(_ref("shop_coupons"), None)
    coupon = coupon_row(
        {"id": 31, "code": "SPRING10", "discount_type": "percent", "amount": "10"}, SITE
    )
    a.texts += ["SPRING10", "15", "", ""]
    a.choices += [0]
    bench.provider.do_edit_coupon(_ref("shop_coupons"), coupon)
    bench.provider.do_trash_coupon(_ref("shop_coupons"), coupon)
    assert [(m, r) for m, r, _b in api.sent] == [
        ("POST", "wc/v3/coupons"),
        ("POST", "wc/v3/coupons/31"),
        ("DELETE", "wc/v3/coupons/31"),
    ]
    assert api.sent[1][2] == {"amount": "15"}


# -- Package 10 --------------------------------------------------------------------------


def test_change_setting_previews_and_a_password_is_refused(bench) -> None:
    raw = {"id": "woocommerce_currency", "label": "Currency", "type": "select", "value": "USD",
           "options": {"USD": "US dollar", "EUR": "Euro"}}  # fmt: skip
    bench.answers.choices += [1]
    bench.provider.do_change_shop_setting(
        _ref("shop_settings"), setting_row("general", "General", raw, SITE)
    )
    assert bench.api.sent == [
        ("POST", "wc/v3/settings/general/woocommerce_currency", {"value": "EUR"})
    ]
    secret = setting_row(
        "advanced", "Advanced", {"id": "k", "label": "Key", "type": "password"}, SITE
    )
    bench.provider.do_change_shop_setting(_ref("shop_settings"), secret)
    assert "password-style" in bench.said[-1] and len(bench.api.sent) == 1


# -- Package 11 --------------------------------------------------------------------------


def test_new_and_edit_event_and_a_recurring_one_is_refused(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Fair", "2026-12-01 10:00", "2026-12-01 12:00", "", ""]
    a.choices += [0, 1]  # has times; The Hall
    bench.provider.do_new_here(_ref("events"), None)
    assert api.sent[0][1] == "tribe/events/v1/events" and api.sent[0][2]["venue"] == 5
    row = event_row(EVENT, SITE)
    a.texts += ["Open Day", "2026-11-21 11:00", "2026-11-21 16:00", "America/New_York", ""]
    a.choices += [0]
    bench.provider.do_edit_event(_ref("events"), row)
    assert api.sent[1] == (
        "POST",
        "tribe/events/v1/events/21",
        {"start_date": "2026-11-21 11:00:00"},
    )
    recurring = event_row({**EVENT, "recurring": True}, SITE)
    bench.provider.do_edit_event(_ref("events"), recurring)
    bench.provider.do_trash_event(_ref("events"), recurring)
    assert len(api.sent) == 2 and "Events Calendar Pro" in bench.said[-1]
    bench.provider.do_trash_event(_ref("events"), row)
    assert api.sent[-1] == ("DELETE", "tribe/events/v1/events/21", None)


def test_events_between_dates_reports_them(bench) -> None:
    bench.answers.texts += ["2026-11-01", "2026-11-30"]
    bench.provider.do_events_between(_ref("events"), None)
    assert "Open Day" in bench.answers.reports[-1]["text"]


def test_venues_and_organizers_new_edit_trash(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Hall", "", "Town", "", "", "", "", ""]
    bench.provider.do_new_venue(_ref("events_venues"), None)
    venue = venue_row({"id": 5, "venue": "The Hall", "city": "Town"}, SITE)
    a.texts += ["The Hall", "", "City", "", "", "", "", ""]
    bench.provider.do_edit_venue(_ref("events_venues"), venue)
    bench.provider.do_trash_venue(_ref("events_venues"), venue)
    organizer = organizer_row({"id": 6, "organizer": "Ann"}, SITE)
    a.texts += ["Ann", "555", "", ""]
    bench.provider.do_edit_organizer(_ref("events_organizers"), organizer)
    a.texts += ["Bob", "", "", ""]
    bench.provider.do_new_organizer(_ref("events_organizers"), None)
    bench.provider.do_trash_organizer(_ref("events_organizers"), organizer)
    assert [(m, r) for m, r, _b in api.sent] == [
        ("POST", "tribe/events/v1/venues"),
        ("POST", "tribe/events/v1/venues/5"),
        ("DELETE", "tribe/events/v1/venues/5"),
        ("POST", "tribe/events/v1/organizers/6"),
        ("POST", "tribe/events/v1/organizers"),
        ("DELETE", "tribe/events/v1/organizers/6"),
    ]
    assert api.sent[1][2] == {"city": "City"} and api.sent[3][2] == {"phone": "555"}


# -- Package 12 --------------------------------------------------------------------------


def test_search_appearance_and_edit_seo(bench) -> None:
    raw = {"id": 4, "type": "post", "title": {"raw": "Hello"},
           "meta": {"_yoast_wpseo_title": "", "_yoast_wpseo_metadesc": "Old"},
           "yoast_head_json": {"title": "Hello", "description": "Old"}}  # fmt: skip
    row = seo_row(raw, SITE)
    bench.provider.do_search_appearance(_ref("seo"), row)
    assert bench.answers.reports[-1]["text"].startswith("Title: Hello")
    bench.answers.texts += ["Hello there", "New words", "radio", "", "", ""]  # + social
    bench.answers.choices += [0]
    bench.provider.do_edit_seo(_ref("seo"), row)
    assert bench.api.sent == [
        ("POST", "wp/v2/posts/4",
         {"meta": {"_yoast_wpseo_title": "Hello there", "_yoast_wpseo_metadesc": "New words"}}),
    ]  # fmt: skip
    assert any("Focus keyphrase" in line for line in bench.answers.previews[0]["lines"])


# -- Package 13 --------------------------------------------------------------------------


def _form() -> WbRow:
    return WbRow("form", SITE, "2", {"form": "Signup", "entries": "3"}, "", route="baf/v1/forms/2",
                 status="active", subkind="qaf")  # fmt: skip


def test_qaf_status_settings_views_and_search(bench) -> None:
    a, api = bench.answers, bench.api
    a.choices += [1]  # draft, inactive -> inactive
    bench.provider.do_change_form_status(_ref("forms"), _form())
    a.choices += [1]
    a.texts += ["12"]
    bench.provider.do_form_settings(_ref("forms"), _form())
    bench.provider.do_show_views(_ref("forms"), _form())
    a.texts += ["Ann"]
    bench.provider.do_search_responses(_ref("forms"), _form())
    assert api.sent == [
        ("POST", "baf/v1/forms/2", {"status": "inactive"}),
        ("POST", "baf/v1/forms/2", {"settings": {"ajax_submission": True, "rate_limit_count": 12}}),
    ]
    assert a.reports[0]["text"] == "Map: map view of Signup, draft"
    assert "name: Ann" in a.reports[1]["text"]


def test_delete_form_needs_its_name_typed(bench) -> None:
    a = bench.answers
    a.texts += ["signup"]
    bench.provider.do_delete_form(_ref("forms"), _form())
    assert bench.api.sent == [] and "did not match" in bench.said[-1]
    a.texts += ["Signup"]
    bench.provider.do_delete_form(_ref("forms"), _form())
    assert bench.api.sent == [("DELETE", "baf/v1/forms/2", None)]
    assert "3 responses" in a.previews[0]["lines"][1]


def test_star_and_read_work_on_a_qaf_response(bench) -> None:
    entry = WbRow("form_entry", SITE, "8", {"form": "Signup"}, "", route="baf/v1/entries/8",
                  subkind="qaf", raw={"is_starred": False, "is_read": False})  # fmt: skip
    assert bench.provider.refusal_for("wordpress.workbench.toggle_starred", entry) == ""
    bench.provider.do_toggle_starred(_ref("form_entries"), entry)
    bench.provider.do_toggle_read(_ref("form_entries"), entry)
    assert bench.api.sent == [
        ("POST", "baf/v1/entries/8", {"is_starred": True}),
        ("POST", "baf/v1/entries/8", {"is_read": True}),
    ]


def test_changes_need_workbench_access(bench) -> None:
    bench.provider.access_store.set("s1", Access.READ_ONLY)
    bench.provider.do_new_product(_ref("shop"), None)
    assert bench.answers.previews == [] and "Workbench access" in bench.said[-1]
    assert "Workbench access" in bench.provider.refusal_for(
        "wordpress.workbench.refund_order", _order()
    )
