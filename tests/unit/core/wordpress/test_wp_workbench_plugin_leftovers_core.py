"""The Packages 8 to 13 leftovers, wx-free: loaders, rows, bodies and the checked write."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import ShopValueError
from quill.core.wordpress.workbench_edit import EditConflict
from quill.core.wordpress.workbench_plugin_write import changed_since, checked_write, not_kept
from quill.core.wordpress.workbench_shop import load_shop
from quill.core.wordpress.workbench_shop_care import CustomerEdit, customer_body, webhook_body
from quill.core.wordpress.workbench_shop_setup import location_body, rate_body


class Api:
    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.posts: list[tuple[str, Any]] = []

    def get(self, route: str, **_p: Any) -> Any:
        found = self.answers.get(route, [])
        if isinstance(found, Exception):
            raise found
        return found

    def iter_collection(self, route: str, *_a: Any, **_k: Any):
        found = self.get(route)
        yield from found if isinstance(found, list) else []

    def post(self, route: str, body: Any) -> Any:
        self.posts.append((route, body))
        return {**self.answers.get(route, {}), **body}


def _ctx(api: Api) -> Any:
    info = SimpleNamespace(namespaces=("wc/v3", "tribe/events/v1"), routes=())
    return SimpleNamespace(api=api, name="Radio", info=info, url="https://radio.example")


def test_the_new_shop_nodes_load_through_load_shop() -> None:
    api = Api({
        "wc/v3/products/reviews": [
            {
                "id": 1,
                "product_name": "Mug",
                "reviewer": "Ann",
                "reviewer_email": "ann@example.org",
                "rating": 5,
                "status": "approved",
                "review": "Good",
            }
        ],
        "wc/v3/webhooks": [
            {
                "id": 4,
                "name": "Orders",
                "topic": "order.created",
                "status": "active",
                "secret": "s3cret",
            }
        ],
        "wc/v3/shipping/zones": [{"id": 0, "name": "Everywhere else"}, {"id": 3, "name": "US"}],
        "wc/v3/shipping/zones/3/locations": [{"code": "US", "type": "country"}],
        "wc/v3/shipping/zones/3/methods": [
            {"title": "Flat rate", "enabled": True, "settings": {"cost": {"value": "5"}}}
        ],
        "wc/v3/taxes": [{"id": 12, "name": "State", "rate": "5.6", "country": "US"}],
        "wc/v3/taxes/classes": [{"slug": "reduced-rate", "name": "Reduced rate"}],
        "wc/v3/products/attributes": [{"id": 2, "name": "Size", "slug": "pa_size"}],
        "wc/v3/products/brands": WordPressApiError("No route", status=404),
    })
    ctx = _ctx(api)
    review = load_shop(ctx, "shop", "reviews", {})[0]
    assert "ann@example.org" not in str(review.raw) + review.detail + str(review.cells)
    hook = load_shop(ctx, "shop", "webhooks", {})[0]
    assert "s3cret" not in str(hook.raw) + hook.detail
    zones = load_shop(ctx, "shop", "shipping", {})
    assert zones[1].cells == {
        "zone": "US",
        "locations": "country US",
        "methods": "Flat rate, on, cost 5",
    }
    assert load_shop(ctx, "shop", "taxes", {})[0].cells["rate"] == "5.6 percent"
    assert load_shop(ctx, "shop", "tax_classes", {})[0].key == "reduced-rate"
    assert load_shop(ctx, "shop", "attributes", {})[0].title == "Size"
    with pytest.raises(WordPressApiError, match="no brands"):
        load_shop(ctx, "shop", "brands", {})


def test_event_terms_load_through_the_events_loader() -> None:
    from quill.core.wordpress.workbench_events import load_events

    api = Api({
        "tribe/events/v1/tags": {"tags": [{"id": 5, "name": "Free", "count": 3}], "total_pages": 1}
    })
    rows = load_events(_ctx(api), "tags", {})
    assert rows[0].kind == "tribe_tag" and rows[0].cells["events"] == "3"


def test_bodies_check_what_they_are_given() -> None:
    assert location_body("country us, postcode 85*") == [
        {"code": "US", "type": "country"},
        {"code": "85*", "type": "postcode"},
    ]
    with pytest.raises(ShopValueError, match="not a location"):
        location_body("planet Mars")
    with pytest.raises(ShopValueError, match="percentage"):
        rate_body({}, {"rate": "8%"})
    with pytest.raises(ShopValueError, match="https"):
        webhook_body("Orders", "order.created", "http://example.org")
    old = {"email": "a@example.org", "billing": {"city": "Tucson"}}
    assert customer_body(old, CustomerEdit("billing", {"city": "Tucson", "postcode": "85701"})) == {
        "billing": {"postcode": "85701"}
    }
    with pytest.raises(ShopValueError, match="@"):
        customer_body(old, CustomerEdit("account", {"email": "nobody"}))


def test_checked_write_refuses_a_conflict_verifies_and_keeps_the_undo() -> None:
    loaded = {"name": "US", "billing": {"city": "Tucson"}}
    assert changed_since(loaded, {"name": "UK"}, {"name": "X"}) == ["name"]
    assert changed_since(loaded, {"billing": {"city": "Mesa"}}, {"billing": {"city": "X"}}) == [
        "billing.city"
    ]
    assert not_kept({"name": "X", "secret": "s"}, {"name": "Y"}) == ("name",)
    api = Api({"r": {"name": "UK"}})
    with pytest.raises(EditConflict):
        checked_write(api, "r", {"name": "X"}, {"name": "US"}, name="Zone", site="Radio")
    assert api.posts == []
    api = Api({"r": {"name": "US"}})
    written = checked_write(api, "r", {"name": "X"}, {"name": "US"}, name="Zone", site="Radio")
    assert written.undo == {"name": "US"} and written.not_kept == ()
