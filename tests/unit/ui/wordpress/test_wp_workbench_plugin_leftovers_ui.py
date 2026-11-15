"""The Packages 8 to 13 leftovers in the Workbench window: every new command, called.

WooCommerce's reviews, shipping zones, taxes, webhooks, attributes, brands,
customers' details and variations; The Events Calendar's categories and tags;
Yoast SEO's social fields and its bulk editor. The real provider and frame
over a fake site that keeps its objects, so the conflict check (a re-read),
the verify after a save and Ctrl+Z (the Change History's undo) are exercised,
not only the request sent. Shapes are the test site's public index's and, for
Yoast's bulk editor, Yoast's own source.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_event_terms import term_row  # noqa: E402
from quill.core.wordpress.workbench_events import event_row  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.wordpress.workbench_seo import seo_row  # noqa: E402
from quill.core.wordpress.workbench_shop_care import review_row, webhook_row  # noqa: E402
from quill.core.wordpress.workbench_shop_catalog import product_row  # noqa: E402
from quill.core.wordpress.workbench_shop_reports import customer_row  # noqa: E402
from quill.core.wordpress.workbench_shop_setup import (  # noqa: E402
    rate_row,
    tax_class_row,
    zone_row,
)
from quill.core.wordpress.workbench_shop_setup import term_row as shop_term_row  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"
ALL_CAPS = (
    "manage_options",
    "edit_posts",
    "list_users",
    "edit_users",
    "manage_woocommerce",
    "moderate_comments",
    "manage_categories",
    "wpseo_manage_options",
)


def _review(rid: int, status: str = "hold") -> dict[str, Any]:
    return {
        "id": rid,
        "product_id": 9,
        "product_name": "Mug",
        "status": status,
        "reviewer": "Ann",
        "reviewer_email": "ann@example.org",
        "review": "Lovely",
        "rating": 4,
    }


class FakeApi:
    """A site that keeps its objects: a POST merges into the object, a GET reads it back."""

    def __init__(self) -> None:
        self.caps = set(ALL_CAPS)
        self.sent: list[tuple[str, str, Any]] = []
        self.objects: dict[str, Any] = {
            "wc/v3/products/reviews/1": _review(1),
            "wc/v3/products/reviews/2": _review(2),
            "wc/v3/webhooks/4": {"id": 4, "name": "Orders", "status": "active"},
            "wc/v3/customers/7": {
                "id": 7,
                "first_name": "Ann",
                "last_name": "Lee",
                "email": "ann@example.org",
                "billing": {"city": "Tucson", "email": "ann@example.org"},
                "shipping": {"city": "Tucson"},
            },
            "wc/v3/products/9/variations/31": {
                "id": 31,
                "attributes": [{"option": "Large"}],
                "regular_price": "14.00",
                "sale_price": "",
                "stock_quantity": 3,
                "status": "publish",
            },
            "wc/v3/shipping/zones/3": {"id": 3, "name": "US"},
            "wc/v3/shipping/zones/3/locations": [{"code": "US", "type": "country"}],
            "wc/v3/shipping/zones/3/methods/8": {
                "instance_id": 8,
                "enabled": True,
                "settings": {"cost": {"value": "5.00"}},
            },
            "wc/v3/taxes/12": {
                "id": 12,
                "name": "State",
                "rate": "5.6000",
                "country": "US",
                "state": "AZ",
                "class": "standard",
            },
            "wc/v3/products/attributes/2": {"id": 2, "name": "Size"},
            "wc/v3/products/attributes/2/terms/6": {"id": 6, "name": "Small"},
            "wc/v3/products/brands/5": {"id": 5, "name": "Acme"},
            "tribe/events/v1/categories/40": {"id": 40, "name": "Music"},
            "tribe/events/v1/events/21": {
                "id": 21,
                "title": "Open Day",
                "categories": [{"id": 40, "name": "Music"}],
                "tags": [],
            },
        }
        self.bulk = {
            4: {
                "id": 4,
                "title": "Hello",
                "seo_title": "",
                "meta_description": "Old",
                "social_title": "",
                "social_description": "",
                "focus_keyphrase": "",
                "editable": True,
            },
        }

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            caps = dict.fromkeys(self.caps, True)
            return {"id": 1, "name": "Jeff", "roles": ["administrator"], "capabilities": caps}
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", "wc/v3", "tribe/events/v1", "yoast/v1"]}
        if route == "yoast/v1/bulk_editor/posts":
            wanted = params.get("include") or list(self.bulk)
            if params.get("content_type") == "page":
                return {"posts": []}
            return {"posts": [copy.deepcopy(self.bulk[i]) for i in wanted if i in self.bulk]}
        if route == "tribe/events/v1/categories":
            return {
                "categories": [{"id": 40, "name": "Music"}, {"id": 41, "name": "Kids"}],
                "total_pages": 1,
            }
        if route == "tribe/events/v1/tags":
            return {"tags": [{"id": 50, "name": "Free"}], "total_pages": 1}
        return copy.deepcopy(self.objects.get(route, []))

    def iter_collection(self, route: str, *_a: Any, **_k: Any):
        if route.endswith("/variations"):
            yield copy.deepcopy(self.objects["wc/v3/products/9/variations/31"])
        if route.endswith("/terms"):
            yield copy.deepcopy(self.objects["wc/v3/products/attributes/2/terms/6"])

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.sent.append(("POST", route, copy.deepcopy(body)))
        if route.startswith("yoast/v1/bulk_editor/update_"):
            for item in body["items"]:
                self.bulk[item["id"]].update({k: v for k, v in item.items() if k != "id"})
            return {"results": [{"id": i["id"], "success": True} for i in body["items"]]}
        found = self.objects.get(route)
        if isinstance(found, dict):
            for key, value in body.items():
                if isinstance(value, dict) and isinstance(found.get(key), dict):
                    found[key].update(value)
                else:
                    found[key] = value
            if route.startswith("wc/v3/shipping/") and "settings" in body:
                found["settings"] = {k: {"value": v} for k, v in body["settings"].items()}
            return copy.deepcopy(found)
        if isinstance(found, list):
            self.objects[route] = copy.deepcopy(body)
            return copy.deepcopy(body)
        return {"id": 500, "slug": "food", **(body if isinstance(body, dict) else {})}

    def delete(self, route: str, **params: Any) -> Any:
        self.sent.append(("DELETE", route, params or None))
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


def _undo(bench) -> str:
    return bench.provider.history.undo()


# -- reviews -----------------------------------------------------------------------------


def test_reviews_approve_a_selection_with_an_outcome_each_and_undo(bench, monkeypatch) -> None:
    api = bench.api
    rows = [review_row(_review(1), SITE), review_row(_review(2), SITE)]
    assert "ann@example.org" not in rows[0].detail + str(rows[0].cells)
    api.objects["wc/v3/products/reviews/2"]["status"] = "spam"  # changed since it was read
    monkeypatch.setattr(bench.provider, "selected_rows", lambda: rows)
    bench.provider.do_approve_review(_ref("shop_reviews"), rows[0])
    assert api.sent == [("POST", "wc/v3/products/reviews/1", {"status": "approved"})]
    report = bench.answers.reports[-1]["text"]
    assert "approved" in report and "changed on Community Radio" in report
    assert "1 done, 1 not done" in bench.said[-1]
    assert "Put 1 back" in _undo(bench)
    assert api.sent[-1] == ("POST", "wc/v3/products/reviews/1", {"status": "hold"})


def test_hold_spam_edit_reply_and_trash_a_review(bench) -> None:
    a, api = bench.answers, bench.api
    row = review_row(_review(1, "approved"), SITE)
    api.objects["wc/v3/products/reviews/1"]["status"] = "approved"
    bench.provider.do_hold_review(_ref("shop_reviews"), row)
    api.objects["wc/v3/products/reviews/1"]["status"] = "approved"
    bench.provider.do_spam_review(_ref("shop_reviews"), row)
    a.texts += ["Lovely mug", "5"]
    bench.provider.do_edit_review(_ref("shop_reviews"), row)
    a.texts += ["Thank you"]
    bench.provider.do_reply_review(_ref("shop_reviews"), row)
    bench.provider.do_trash(_ref("shop_reviews"), row)  # Delete
    assert [(m, r) for m, r, _b in api.sent] == [
        ("POST", "wc/v3/products/reviews/1"),
        ("POST", "wc/v3/products/reviews/1"),
        ("POST", "wc/v3/products/reviews/1"),
        ("POST", "wp/v2/comments"),
        ("DELETE", "wc/v3/products/reviews/1"),
    ]
    assert api.sent[2][2] == {"review": "Lovely mug", "rating": 5}
    assert api.sent[3][2] == {"post": 9, "parent": 1, "content": "Thank you"}
    _undo(bench)
    assert api.sent[-1] == ("POST", "wc/v3/products/reviews/1", {"status": "untrash"})


# -- webhooks -----------------------------------------------------------------------------


def test_webhooks_new_toggle_delete_and_never_a_secret(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Orders to Sheets", "https://hooks.example.org/x"]
    a.choices += [0]
    bench.provider.do_new_here(_ref("shop_webhooks"), None)
    assert api.sent[0] == (
        "POST",
        "wc/v3/webhooks",
        {
            "name": "Orders to Sheets",
            "topic": "order.created",
            "delivery_url": "https://hooks.example.org/x",
            "status": "active",
        },
    )
    hook = webhook_row({"id": 4, "name": "Orders", "status": "active", "secret": "s3cret"}, SITE)
    assert "s3cret" not in str(hook.raw) + hook.detail
    bench.provider.do_toggle_webhook(_ref("shop_webhooks"), hook)
    assert api.sent[-1] == ("POST", "wc/v3/webhooks/4", {"status": "paused"})
    bench.provider.do_delete_webhook(_ref("shop_webhooks"), hook)
    assert api.sent[-1] == ("DELETE", "wc/v3/webhooks/4", {"force": True})


# -- customers and variations -----------------------------------------------------------------


def test_customer_details_and_edit_with_undo(bench) -> None:
    a, api = bench.answers, bench.api
    bench.provider.ensure(bench.provider.ctx(SITE))
    row = customer_row({"id": 7, "first_name": "Ann", "last_name": "Lee"}, SITE)
    bench.provider.do_customer_details(_ref("shop_customers"), row)
    assert "Email: ann@example.org" in a.reports[-1]["text"]
    a.choices += [1]  # billing address
    a.texts += ["", "", "", "", "", "Phoenix", "", "", "", ""]
    bench.provider.do_edit_customer(_ref("shop_customers"), row)
    assert api.sent == [("POST", "wc/v3/customers/7", {"billing": {"city": "Phoenix"}})]
    assert "Billing City: Tucson becomes Phoenix." in a.previews[-1]["lines"]
    _undo(bench)
    assert api.sent[-1] == ("POST", "wc/v3/customers/7", {"billing": {"city": "Tucson"}})


def test_customer_details_are_refused_to_a_role_that_cannot_list_people(bench) -> None:
    bench.api.caps.discard("list_users")
    bench.provider.ensure(bench.provider.ctx(SITE))
    row = customer_row({"id": 7, "first_name": "Ann"}, SITE)
    assert bench.provider.refusal_for("wordpress.workbench.customer_details", row)
    bench.provider.do_customer_details(_ref("shop_customers"), row)
    assert bench.answers.reports == [] and "cannot" in bench.said[-1]


def test_edit_a_variation(bench) -> None:
    a, api = bench.answers, bench.api
    product = product_row({"id": 9, "name": "Mug", "type": "variable"}, SITE)
    a.choices += [0, 0]  # the variation, then for sale
    a.texts += ["15.00", "", "3"]
    bench.provider.do_edit_variation(_ref("shop"), product)
    assert api.sent == [("POST", "wc/v3/products/9/variations/31", {"regular_price": "15.00"})]
    _undo(bench)
    assert api.sent[-1][2] == {"regular_price": "14.00"}


# -- shipping, taxes, attributes, brands ---------------------------------------------------------


def _zone() -> WbRow:
    api = FakeApi()
    return zone_row(
        {"id": 3, "name": "US"},
        api.objects["wc/v3/shipping/zones/3/locations"],
        [api.objects["wc/v3/shipping/zones/3/methods/8"]],
        SITE,
    )


def test_shipping_zones_new_rename_locations_methods_delete(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Local"]
    bench.provider.do_new_here(_ref("shop_shipping"), None)
    a.texts += ["United States"]
    bench.provider.do_rename_shop_item(_ref("shop_shipping"), _zone())
    a.texts += ["country US, state CA:ON"]
    bench.provider.do_zone_locations(_ref("shop_shipping"), _zone())
    a.choices += [0, 1]  # the flat rate, change its cost
    a.texts += ["6.50"]
    bench.provider.do_zone_methods(_ref("shop_shipping"), _zone())
    bench.provider.do_delete_shop_item(_ref("shop_shipping"), _zone())
    assert api.sent == [
        ("POST", "wc/v3/shipping/zones", {"name": "Local"}),
        ("POST", "wc/v3/shipping/zones/3", {"name": "United States"}),
        (
            "POST",
            "wc/v3/shipping/zones/3/locations",
            [{"code": "US", "type": "country"}, {"code": "CA:ON", "type": "state"}],
        ),
        ("POST", "wc/v3/shipping/zones/3/methods/8", {"settings": {"cost": "6.50"}}),
        ("DELETE", "wc/v3/shipping/zones/3", {"force": True}),
    ]
    assert "cannot be undone" in _undo(bench)  # a delete for good keeps no undo


def test_zone_locations_refuse_when_changed_on_the_site(bench) -> None:
    bench.api.objects["wc/v3/shipping/zones/3/locations"] = [{"code": "GB", "type": "country"}]
    bench.answers.texts += ["country US, country CA"]
    bench.provider.do_zone_locations(_ref("shop_shipping"), _zone())
    assert bench.api.sent == [] and "Nothing was sent" in bench.said[-1]


def test_tax_rates_and_classes(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["City", "2", "US", "AZ", "", "Tucson"]
    bench.provider.do_new_here(_ref("shop_taxes"), None)
    rate = rate_row(api.objects["wc/v3/taxes/12"], SITE)
    a.texts += ["State", "5.7", "US", "AZ", "", ""]
    bench.provider.do_edit_tax_rate(_ref("shop_taxes"), rate)
    bench.provider.do_delete_shop_item(_ref("shop_taxes"), rate)
    assert "Made State again" in _undo(bench)
    a.texts += ["Food"]
    bench.provider.do_new_here(_ref("shop_tax_classes"), None)
    bench.provider.do_delete_shop_item(
        _ref("shop_tax_classes"), tax_class_row({"name": "Food", "slug": "food"}, SITE)
    )
    assert [(m, r) for m, r, _b in api.sent] == [
        ("POST", "wc/v3/taxes"),
        ("POST", "wc/v3/taxes/12"),
        ("DELETE", "wc/v3/taxes/12"),
        ("POST", "wc/v3/taxes"),
        ("POST", "wc/v3/taxes/classes"),
        ("DELETE", "wc/v3/taxes/classes/food"),
    ]
    assert api.sent[1][2] == {"rate": "5.7"} and api.sent[3][2]["rate"] == "5.6000"
    assert "every rate in it" in " ".join(a.previews[-1]["lines"]).lower()


def test_attributes_terms_and_brands(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Colour"]
    bench.provider.do_new_here(_ref("shop_attributes"), None)
    size = shop_term_row("shop_attribute", {"id": 2, "name": "Size"}, SITE)
    a.choices += [1]  # Add a term
    a.texts += ["Large"]
    bench.provider.do_attribute_terms(_ref("shop_attributes"), size)
    a.choices += [0, 0]  # Small, rename it
    a.texts += ["Petite"]
    bench.provider.do_attribute_terms(_ref("shop_attributes"), size)
    bench.provider.do_delete_shop_item(_ref("shop_attributes"), size)
    a.texts += ["Bravo"]
    bench.provider.do_new_here(_ref("shop_brands"), None)
    a.texts += ["Acme Ltd"]
    bench.provider.do_rename_shop_item(
        _ref("shop_brands"), shop_term_row("shop_brand", {"id": 5, "name": "Acme"}, SITE)
    )
    assert api.sent == [
        ("POST", "wc/v3/products/attributes", {"name": "Colour"}),
        ("POST", "wc/v3/products/attributes/2/terms", {"name": "Large"}),
        ("POST", "wc/v3/products/attributes/2/terms/6", {"name": "Petite"}),
        ("DELETE", "wc/v3/products/attributes/2", {"force": True}),
        ("POST", "wc/v3/products/brands", {"name": "Bravo"}),
        ("POST", "wc/v3/products/brands/5", {"name": "Acme Ltd"}),
    ]
    _undo(bench)
    assert api.sent[-1] == ("POST", "wc/v3/products/brands/5", {"name": "Acme"})


# -- event categories and tags -------------------------------------------------------------------


def test_event_categories_and_tags(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Theatre"]
    bench.provider.do_new_here(_ref("events_categories"), None)
    a.texts += ["Sale"]
    bench.provider.do_new_here(_ref("events_tags"), None)
    music = term_row("tribe_category", {"id": 40, "name": "Music", "count": 2}, SITE)
    a.texts += ["Live Music"]
    bench.provider.do_rename_event_term(_ref("events_categories"), music)
    bench.provider.do_delete_event_term(_ref("events_categories"), music)
    event = event_row(
        {
            "id": 21,
            "title": "Open Day",
            "start_date": "2026-11-21 10:00:00",
            "end_date": "2026-11-21 16:00:00",
        },
        SITE,
    )
    a.texts += ["Live Music, Kids", "Free"]
    api.objects["tribe/events/v1/events/21"]["categories"] = [{"id": 40, "name": "Live Music"}]
    bench.provider.do_set_event_terms(_ref("events"), event)
    assert api.sent[:4] == [
        ("POST", "tribe/events/v1/categories", {"name": "Theatre"}),
        ("POST", "tribe/events/v1/tags", {"name": "Sale"}),
        ("POST", "tribe/events/v1/categories/40", {"name": "Live Music"}),
        ("DELETE", "tribe/events/v1/categories/40", None),
    ]
    assert "no event category called Live Music" in bench.said[-1]  # the fake list still says Music
    a.texts += ["Music, Kids", "Free"]
    bench.provider.do_set_event_terms(_ref("events"), event)
    assert api.sent[-1] == (
        "POST",
        "tribe/events/v1/events/21",
        {"categories": [40, 41], "tags": [50]},
    )
    _undo(bench)
    assert api.sent[-1] == ("POST", "tribe/events/v1/events/21", {"categories": [40], "tags": []})


# -- Yoast SEO --------------------------------------------------------------------------------


def _seo() -> WbRow:
    return seo_row(
        {
            "id": 4,
            "type": "post",
            "title": {"raw": "Hello"},
            "meta": {},
            "yoast_head_json": {"title": "Hello", "description": "Old"},
        },
        SITE,
    )


def test_edit_seo_goes_through_yoasts_bulk_editor_with_social_fields(bench) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Hello there", "Old", "", "Share me", "", "https://radio.example/p.jpg"]
    a.choices += [0]
    bench.provider.do_edit_seo(_ref("seo"), _seo())
    assert api.sent == [
        (
            "POST",
            "yoast/v1/bulk_editor/update_search",
            {"items": [{"id": 4, "seo_title": "Hello there"}]},
        ),
        (
            "POST",
            "yoast/v1/bulk_editor/update_social",
            {"items": [{"id": 4, "social_title": "Share me"}]},
        ),
    ]
    lines = " ".join(a.previews[-1]["lines"])
    assert "Social title: not set becomes Share me." in lines and "Social image" in lines
    _undo(bench)
    assert api.bulk[4]["seo_title"] == "" and api.bulk[4]["social_title"] == ""


def test_edit_seo_refuses_when_yoast_changed_meanwhile(bench, monkeypatch) -> None:
    a, api = bench.answers, bench.api
    a.texts += ["Hello there", "Old", "", "", "", ""]
    a.choices += [0]
    original = api.get

    def get(route: str, **params: Any) -> Any:
        answer = original(route, **params)
        if route == "yoast/v1/bulk_editor/posts" and a.previews:
            answer["posts"][0]["seo_title"] = "Someone else's"
        return answer

    monkeypatch.setattr(api, "get", get)
    bench.provider.do_edit_seo(_ref("seo"), _seo())
    assert api.sent == [] and "Nothing was sent" in bench.said[-1]


class _FakeList:
    """Stands in for the ListWindow: Enter on the first row, once."""

    made: list[_FakeList] = []

    def __init__(self, _parent: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.rows = list(kwargs["rows"])
        _FakeList.made.append(self)

    def set_rows(self, rows: list[str], keep: int | None = None) -> None:
        self.rows = rows

    def Destroy(self) -> None:  # noqa: N802 - wx's name
        pass


def test_bulk_seo_editor_changes_an_item_where_it_stands(bench, monkeypatch) -> None:
    a, api = bench.answers, bench.api
    _FakeList.made.clear()
    monkeypatch.setattr(dlg, "ListWindow", _FakeList)
    a.texts += ["Hello, radio", "New words"]
    monkeypatch.setattr(
        bench.provider, "show_modal", lambda window, _label: window.kwargs["on_enter"](0)
    )
    bench.provider.do_bulk_seo(_ref("seo"), _seo())
    window = _FakeList.made[0]
    assert window.rows[0].startswith("Hello: SEO title 12 characters, description 9")
    assert api.sent == [
        (
            "POST",
            "yoast/v1/bulk_editor/update_search",
            {"items": [{"id": 4, "seo_title": "Hello, radio", "meta_description": "New words"}]},
        )
    ]
    assert "Meta description: Old becomes New words." in a.previews[-1]["lines"]
    _undo(bench)
    assert api.bulk[4]["meta_description"] == "Old"


def test_new_rows_need_their_capability(bench) -> None:
    bench.api.caps -= {"wpseo_manage_options", "manage_woocommerce"}
    bench.provider.ensure(bench.provider.ctx(SITE))
    assert bench.provider.refusal_for("wordpress.workbench.bulk_seo", _seo())
    assert bench.provider.refusal_for("wordpress.workbench.zone_methods", _zone())
