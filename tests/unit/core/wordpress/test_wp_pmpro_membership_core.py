"""Paid Memberships Pro in the Workbench, wx-free (complete.md WP-C).

Reads go through PMPro's read-only abilities with the bracketed ``input[...]``
query WordPress's Abilities API expects of a GET; no card or billing detail
reaches a row; Change Membership Level and Cancel Membership preview the
gateway consequence; membership orders are never confused with shop orders.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import workbench_pmpro_change as pc
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_load import SiteContext
from quill.core.wordpress.workbench_pmpro import load_pmpro

RUN = "wp-abilities/v1/abilities/{}/run"
CARD = {
    "cardtype": "Visa",
    "accountnumber": "XXXX4242",
    "expirationmonth": "12",
    "expirationyear": "2030",
    "billing": {"name": "Ann Lee", "street": "1 High St", "phone": "0123"},
    "billing_street": "1 High St",
}


def _ability(name: str, *, readonly: bool = True, props: tuple[str, ...] = ()) -> dict:
    return {
        "name": name,
        "label": name,
        "meta": {"annotations": {"readonly": readonly}},
        "input_schema": {"properties": {p: {} for p in props}},
    }


class FakeApi:
    site_name = "Radio"

    def __init__(self, abilities: list[dict], answers: dict[str, Any] | None = None) -> None:
        self.abilities = abilities
        self.answers = answers or {}
        self.requests: list[tuple[str, str, dict[str, Any]]] = []
        self.posts: list[tuple[str, Any]] = []

    def iter_collection(self, route: str, *_a: Any, **_k: Any):
        assert route == "wp-abilities/v1/abilities"
        yield from self.abilities

    def request(self, method: str, route: str, **kw: Any) -> Any:
        params = dict(kw.get("params") or {})
        self.requests.append((method, route, params))
        answer = self.answers.get(route)

        class _R:
            payload = answer(params) if callable(answer) else answer

        return _R()

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.posts.append((route, body))
        return self.answers.get(route, True)


def _ctx(api: FakeApi) -> SiteContext:
    return SiteContext("Radio", api, url="https://radio.example")  # type: ignore[arg-type]


ORDER = {
    "id": 9,
    "code": "A1B2",
    "status": "success",
    "total": "10.00",
    "gateway": "stripe",
    "user_id": 4,
    "membership_level_id": 2,
    "timestamp": "2026-11-01",
    **CARD,
}


def test_orders_are_read_by_get_with_bracketed_inputs_and_carry_no_card_details() -> None:
    api = FakeApi(
        [_ability("pmpro/orders-query")],
        {RUN.format("pmpro/orders-query"): {"items": [ORDER], "total": 1}},
    )
    rows = load_pmpro(_ctx(api), "orders")
    assert api.requests == [
        ("GET", RUN.format("pmpro/orders-query"), {"input[limit]": 50, "input[page]": 1})
    ]
    row = rows[0]
    assert row.detail.startswith("Membership order A1B2. Success, total 10.00, gateway stripe")
    seen = repr((row.cells, row.detail, row.raw))
    for secret in ("Visa", "4242", "2030", "High St", "Ann Lee", "0123"):
        assert secret not in seen, secret
    assert row.raw["code"] == "A1B2" and row.raw["gateway"] == "stripe"


def test_a_query_ability_not_marked_read_only_is_refused() -> None:
    api = FakeApi([_ability("pmpro/orders-query", readonly=False)])
    with pytest.raises(WordPressApiError, match="not marked read-only"):
        load_pmpro(_ctx(api), "orders")
    assert api.requests == []


def test_a_site_without_the_abilities_says_which_versions_bring_them() -> None:
    row = load_pmpro(_ctx(FakeApi([])), "levels")[0]
    assert row.kind == "fact" and "WordPress 6.9" in row.detail and "3.9" in row.detail


def test_without_payment_details_strips_nested_billing() -> None:
    clean = pc.without_payment_details({"id": 1, "member": {"name": "Ann", **CARD}, **CARD})
    assert clean == {"id": 1, "member": {"name": "Ann"}}


def _subs(user_id_filter: bool) -> FakeApi:
    items = [
        {"id": 31, "user_id": 4, "status": "active", "gateway": "stripe",
         "membership_level_id": 2, "billing_amount": "10.00", "cycle_number": 1,
         "cycle_period": "Month", "next_payment_date": "2026-12-01", **CARD},
        {"id": 32, "user_id": 4, "status": "cancelled", "gateway": "paypal"},
        {"id": 33, "user_id": 5, "status": "active", "gateway": "stripe"},
    ]  # fmt: skip
    props = ("user_id", "limit", "page") if user_id_filter else ("limit", "page")
    return FakeApi(
        [_ability("pmpro/subscriptions-query", props=props)],
        {RUN.format("pmpro/subscriptions-query"): {"items": items}},
    )


@pytest.mark.parametrize("takes_user", [True, False])
def test_member_subscriptions_are_only_this_persons_active_ones(takes_user: bool) -> None:
    api = _subs(takes_user)
    found = pc.member_subscriptions(api, 4)  # type: ignore[arg-type]
    assert [s["id"] for s in found or []] == [31]
    assert "cardtype" not in found[0]  # type: ignore[index]
    assert ("input[user_id]" in api.requests[0][2]) is takes_user
    assert pc.member_subscriptions(FakeApi([]), 4) is None  # type: ignore[arg-type]


def test_the_cancel_preview_names_the_subscription_gateway_and_next_payment() -> None:
    subs = pc.member_subscriptions(_subs(True), 4)  # type: ignore[arg-type]
    lines = pc.cancel_preview("Ann", "Radio", {"id": 2, "name": "Gold"}, subs)
    assert lines[0] == "Ann loses Gold on Radio now."
    assert lines[1] == (
        "Paid Memberships Pro also cancels subscription 31 at stripe, 10.00 every 1 Month, "
        "next payment 2026-12-01: no further payments are taken."
    )
    assert "Nothing is refunded" in lines[2] and "cannot be undone" in lines[3]

    unknown = pc.cancel_preview("Ann", "Radio", {"id": 2, "name": "Gold"}, None)
    assert "could not read this person's subscriptions" in unknown[1]
    other_level = pc.cancel_preview("Ann", "Radio", {"id": 7, "name": "Bronze"}, subs)
    assert "no active recurring subscription" in other_level[1]


def test_the_change_preview_says_what_ends_and_that_no_payment_is_taken() -> None:
    subs = pc.member_subscriptions(_subs(True), 4)  # type: ignore[arg-type]
    lines = pc.change_preview(
        "Ann", "Radio", [{"id": 2, "name": "Gold"}], {"id": 3, "name": "Silver"}, subs
    )
    assert lines[0] == "Ann gets Silver on Radio now, with no checkout and no payment taken."
    assert lines[1] == "Gold ends."
    assert "cancels subscription 31 at stripe" in lines[2]
    fresh = pc.change_preview("Bo", "Radio", [], {"id": 3, "name": "Silver"}, None)
    assert "no current membership" in fresh[1] and "Cancel Membership" in fresh[-1]


def test_change_and_cancel_post_to_pmpros_routes_and_a_refusal_is_an_error() -> None:
    api = FakeApi([])
    pc.change_membership(api, 4, 3)  # type: ignore[arg-type]
    pc.cancel_membership(api, 4, 2)  # type: ignore[arg-type]
    assert api.posts == [
        ("pmpro/v1/change_membership_level", {"user_id": 4, "level_id": 3}),
        ("pmpro/v1/cancel_membership_level", {"user_id": 4, "level_id": 2}),
    ]
    api.answers[pc.CANCEL_ROUTE] = False
    with pytest.raises(WordPressApiError, match="did not cancel"):
        pc.cancel_membership(api, 4, 2)  # type: ignore[arg-type]


def test_membership_orders_and_shop_orders_are_told_apart() -> None:
    from quill.core.wordpress.workbench_coverage import classify
    from quill.core.wordpress.workbench_node_help import NODE_HELP, ROW_HELP

    assert "not membership orders" in NODE_HELP["shop_orders"]
    assert "Not a membership order" in ROW_HELP["shop_order"]
    assert "Shop orders are not membership orders" in NODE_HELP["orders"]
    assert "not WooCommerce shop orders" in NODE_HELP["membership_orders"]
    assert "membership order" in ROW_HELP["pmpro"]
    assert classify("/pmpro/v1/cancel_membership_level").status == "covered"
    assert "Cancel Membership" in classify("/pmpro/v1/cancel_membership_level").home
