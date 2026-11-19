"""WooCommerce's payment gateways, its system status and tools, and resending an order's email.

From complete.md 2.3 (Shop): three things a shop manager does from wp-admin
today, each on a route WooCommerce has.

- **Payment Gateways** (``payment_gateways``): each gateway, whether it is on,
  and its customer-facing title. Turn On or Off sends only ``enabled``; no
  setting is read back or shown, because a gateway's settings carry its keys.
- **System Status** (``system_status`` and ``system_status/tools``): the PHP,
  database and WordPress versions core REST does not give, as facts, then each
  of WooCommerce's maintenance tools (clear transients, recount terms...) as a
  row Run Tool runs, after a preview.
- **Resend Order Details** (``orders/{id}/actions/send_order_details``): the
  customer's order details again, for "the receipt never came".

Wx-free; the Workbench's commands are in :mod:`quill.ui.wordpress_workbench_shop_store`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_rows import WbRow, fact_rows

__all__ = [
    "ENVIRONMENT_FACTS",
    "gateway_row",
    "load_gateways",
    "load_status",
    "resend_order_details",
    "run_tool",
    "set_gateway",
    "tool_row",
]

GATEWAYS = f"{SHOP_NAMESPACE}/payment_gateways"
STATUS = f"{SHOP_NAMESPACE}/system_status"
TOOLS = f"{SHOP_NAMESPACE}/system_status/tools"

#: The environment facts System Status says, in this order: key -> what it is called.
ENVIRONMENT_FACTS: tuple[tuple[str, str], ...] = (
    ("version", "WooCommerce"),
    ("wp_version", "WordPress"),
    ("php_version", "PHP"),
    ("mysql_version", "Database"),
    ("server_info", "Web server"),
    ("max_upload_size", "Largest upload, in bytes"),
    ("wp_memory_limit", "WordPress memory limit, in bytes"),
)


def _plain(text: Any) -> str:
    return (
        " ".join(rendered(text).split())
        if isinstance(text, dict)
        else " ".join(str(text or "").split())
    )


def gateway_row(raw: Mapping[str, Any], site: str) -> WbRow:
    """One payment gateway: its name, on or off, and what the customer sees."""
    name = _plain(raw.get("method_title")) or _plain(raw.get("title")) or str(raw.get("id", ""))
    title = _plain(raw.get("title"))
    on = bool(raw.get("enabled"))
    state = "on" if on else "off"
    return WbRow(
        kind="shop_gateway",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "state": state, "title": title},
        detail=(
            f"{name}, {state}. Customers see it as {title or 'its own name'} at checkout. "
            "Its settings, which hold its keys, stay in WooCommerce > Settings > Payments."
        ),
        status="active" if on else "inactive",
        subkind="woocommerce",
        raw={"id": raw.get("id"), "enabled": on, "name": name},
    )


def load_gateways(api: Any, site: str) -> list[WbRow]:
    raw = api.get(GATEWAYS)
    rows = (
        [gateway_row(r, site) for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    )
    return sorted(rows, key=lambda r: (r.status != "active", r.title.lower()))


def set_gateway(api: Any, gateway_id: str, on: bool) -> bool:
    """Turn a gateway on or off; True when WooCommerce kept what was sent."""
    raw = api.post(f"{GATEWAYS}/{gateway_id}", {"enabled": on})
    return bool(raw.get("enabled")) == on if isinstance(raw, dict) else False


def tool_row(raw: Mapping[str, Any], site: str) -> WbRow:
    """One of WooCommerce's maintenance tools, such as Clear transients."""
    name = _plain(raw.get("name")) or str(raw.get("id", ""))
    what = _plain(raw.get("desc")) or _plain(raw.get("description"))
    return WbRow(
        kind="shop_tool",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "value": what},
        detail=f"{name}. {what}".strip(),
        subkind="woocommerce",
        raw={"id": raw.get("id"), "name": name, "action": _plain(raw.get("action"))},
    )


def load_status(api: Any, site: str) -> list[WbRow]:
    """The versions first, as facts, then each tool as a row Run Tool runs."""
    raw = api.get(STATUS)
    environment = raw.get("environment", {}) if isinstance(raw, dict) else {}
    facts = [
        (label, str(environment.get(key)))
        for key, label in ENVIRONMENT_FACTS
        if isinstance(environment, dict) and environment.get(key) not in (None, "")
    ]
    tools = api.get(TOOLS)
    found = (
        [tool_row(t, site) for t in tools if isinstance(t, dict)] if isinstance(tools, list) else []
    )
    return [*fact_rows(site, facts), *found]


def run_tool(api: Any, tool_id: str) -> str:
    """Run one tool; WooCommerce's own sentence about what it did."""
    raw = api.post(f"{TOOLS}/{tool_id}", {"confirm": True})
    if isinstance(raw, dict):
        said = _plain(raw.get("message"))
        if raw.get("success") is False:
            return f"WooCommerce did not run it: {said or 'it gave no reason'}."
        return said or "Done."
    return "Done."


def resend_order_details(api: Any, order_id: int) -> str:
    """Send the customer their order details again; WooCommerce's sentence, or ours."""
    raw = api.post(f"{SHOP_NAMESPACE}/orders/{order_id}/actions/send_order_details", {})
    said = _plain(raw.get("message")) if isinstance(raw, dict) else ""
    return said or "WooCommerce sent the order details to the customer."
