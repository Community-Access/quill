"""complete.md 2.3 (Shop): payment gateways, system status and tools, resending order details."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import workbench_shop_store as store


class Shop:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Any]] = []
        self.gateways = [
            {"id": "cod", "title": "Pay on delivery", "method_title": "Cash on delivery",
             "enabled": False, "settings": {"secret": {"value": "never-shown"}}},
            {"id": "stripe", "title": "Card", "method_title": "Stripe", "enabled": True},
        ]  # fmt: skip

    def get(self, route: str, **_p: Any) -> Any:
        if route == "wc/v3/payment_gateways":
            return self.gateways
        if route == "wc/v3/system_status":
            return {"environment": {"version": "9.4", "php_version": "8.3", "wp_version": "6.9"}}
        if route == "wc/v3/system_status/tools":
            return [{"id": "clear_transients", "name": "WooCommerce transients",
                     "desc": "Clears the product and shop transients cache."}]  # fmt: skip
        return []

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.sent.append((route, body))
        if route.startswith("wc/v3/payment_gateways/"):
            return {"enabled": body["enabled"]}
        if route.endswith("/tools/clear_transients"):
            return {"success": True, "message": "Product transients cleared"}
        return {}


def test_gateways_on_first_and_no_setting_is_kept() -> None:
    rows = store.load_gateways(Shop(), "Shop")
    assert [r.cell("name") for r in rows] == ["Stripe", "Cash on delivery"]
    assert rows[1].cell("state") == "off" and "never-shown" not in repr(rows)


def test_turning_a_gateway_on_sends_only_enabled() -> None:
    shop = Shop()
    assert store.set_gateway(shop, "cod", True)
    assert shop.sent == [("wc/v3/payment_gateways/cod", {"enabled": True})]


def test_status_gives_the_versions_then_the_tools() -> None:
    rows = store.load_status(Shop(), "Shop")
    facts = {r.cell("fact"): r.cell("value") for r in rows if r.kind == "fact"}
    assert facts == {"WooCommerce": "9.4", "WordPress": "6.9", "PHP": "8.3"}
    assert [r.key for r in rows if r.kind == "shop_tool"] == ["clear_transients"]


def test_a_tool_says_what_woocommerce_said() -> None:
    assert store.run_tool(Shop(), "clear_transients") == "Product transients cleared"


def test_resend_order_details_posts_the_action() -> None:
    shop = Shop()
    said = store.resend_order_details(shop, 77)
    assert shop.sent == [("wc/v3/orders/77/actions/send_order_details", {})]
    assert said == "WooCommerce sent the order details to the customer."
