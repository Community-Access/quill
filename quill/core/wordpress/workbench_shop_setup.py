"""WooCommerce's shipping, taxes, attributes and brands in the Workbench, and their loaders.

All through ``wc/v3``, in the shapes the test site's public index gives:

- **Shipping Zones** (``shipping/zones``): each zone with its locations
  (``/{id}/locations``, written whole as ``[{"code", "type"}]``) and methods
  (``/{zone}/methods``: flat rate, free shipping, local pickup, each with
  its own settings). Zone 0, "Locations not covered by your other zones",
  can have methods but no name or locations of its own.
- **Tax Rates** (``taxes``) and **Tax Classes** (``taxes/classes``). A
  class is deleted with its rates, which the preview says.
- **Attributes** (``products/attributes``) and their terms (``/{id}/terms``).
- **Brands** (``products/brands``), only on a site whose index lists it
  (WooCommerce 9.6 and later); otherwise the node says so.

None of these has a Trash: a delete is for good, tier 3, with a preview.
Wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "LOCATION_TYPES",
    "METHOD_KINDS",
    "SIMPLE",
    "load_shop_setup",
    "location_body",
    "location_words",
    "method_lines",
    "rate_body",
    "rate_preview",
    "term_row",
]

ZONES = f"{SHOP_NAMESPACE}/shipping/zones"
TAXES = f"{SHOP_NAMESPACE}/taxes"
TAX_CLASSES = f"{SHOP_NAMESPACE}/taxes/classes"
ATTRIBUTES = f"{SHOP_NAMESPACE}/products/attributes"
BRANDS = f"{SHOP_NAMESPACE}/products/brands"

LOCATION_TYPES = ("country", "state", "postcode", "continent")

METHOD_KINDS: dict[str, str] = {
    "flat_rate": "Flat rate",
    "free_shipping": "Free shipping",
    "local_pickup": "Local pickup",
}
"""The shipping methods WooCommerce itself provides, offered by Add a Method."""

SIMPLE: dict[str, tuple[str, str]] = {
    "shop_zone": ("shipping zone", ZONES),
    "shop_attribute": ("attribute", ATTRIBUTES),
    "shop_brand": ("brand", BRANDS),
    "shop_tax_rate": ("tax rate", TAXES),
}
"""Row kind -> (noun, collection route) for the kinds renamed or deleted the same way."""


# -- rows -----------------------------------------------------------------------------------


def location_words(locations: Sequence[Mapping[str, Any]]) -> str:
    """``[{"code": "US:AZ", "type": "state"}]`` -> ``"state US:AZ"``."""
    parts = [
        f"{loc.get('type', '')} {loc.get('code', '')}".strip()
        for loc in locations
        if isinstance(loc, Mapping)
    ]
    return ", ".join(parts) or "none"


def method_lines(methods: Sequence[Mapping[str, Any]]) -> list[str]:
    """``"Flat rate, on, cost 5.00"`` for each method in a zone."""
    lines = []
    for m in methods:
        if not isinstance(m, Mapping):
            continue
        settings = m.get("settings") if isinstance(m.get("settings"), Mapping) else {}
        cost = (settings or {}).get("cost")
        value = cost.get("value") if isinstance(cost, Mapping) else ""
        title = rendered(m.get("title")) or rendered(m.get("method_title")) or "A method"
        on = "on" if m.get("enabled") else "off"
        lines.append(f"{title}, {on}" + (f", cost {value}" if value else ""))
    return lines


def zone_row(
    raw: Mapping[str, Any],
    locations: Sequence[Mapping[str, Any]],
    methods: Sequence[Mapping[str, Any]],
    site: str,
) -> WbRow:
    name = rendered(raw.get("name")) or "Unnamed zone"
    where = location_words(locations)
    how = method_lines(methods)
    return WbRow(
        kind="shop_zone",
        site=site,
        key=str(raw.get("id", 0)),
        cells={"zone": name, "locations": where, "methods": "; ".join(how) or "none"},
        detail=f"Shipping zone {name}. Locations: {where}. Methods: {'; '.join(how) or 'none'}.",
        subkind="woocommerce",
        raw={
            "name": name,
            "locations": where,
            "methods": "; ".join(how) or "none",
            "_loaded": {"name": name},
            "_locations": [dict(loc) for loc in locations if isinstance(loc, Mapping)],
            "_methods": [dict(m) for m in methods if isinstance(m, Mapping)],
        },
    )


def rate_row(raw: Mapping[str, Any], site: str) -> WbRow:
    name = rendered(raw.get("name")) or "Tax"
    rate = str(raw.get("rate", "") or "0")
    country = str(raw.get("country", "") or "") or "everywhere"
    state = str(raw.get("state", "") or "")
    tax_class = str(raw.get("class", "") or "standard")
    where = f"{country}{' ' + state if state else ''}"
    loaded = {k: raw.get(k) for k in _RATE_KEYS if k in raw}
    return WbRow(
        kind="shop_tax_rate",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "rate": f"{rate} percent", "where": where, "class": tax_class},
        detail=f"{name}, {rate} percent, {where}, the {tax_class} class.",
        subkind="woocommerce",
        raw={
            "name": name,
            "rate": f"{rate} percent",
            "where": where,
            "class": tax_class,
            "_loaded": loaded,
        },
    )


def tax_class_row(raw: Mapping[str, Any], site: str) -> WbRow:
    name = rendered(raw.get("name")) or str(raw.get("slug", ""))
    slug = str(raw.get("slug", "") or "")
    return WbRow(
        kind="shop_tax_class",
        site=site,
        key=slug,
        cells={"name": name, "slug": slug},
        detail=f"The {name} tax class ({slug}).",
        subkind="woocommerce",
        raw={"name": name, "slug": slug},
    )


def term_row(kind: str, raw: Mapping[str, Any], site: str) -> WbRow:
    """An attribute or a brand: its name, slug and how many products use it."""
    name = rendered(raw.get("name")) or "Unnamed"
    slug = str(raw.get("slug", "") or "")
    count = str(raw.get("count", "") or "")
    noun = SIMPLE[kind][0]
    return WbRow(
        kind=kind,
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "slug": slug, "products": count},
        detail=f"The {noun} {name}" + (f", on {count} products." if count else "."),
        subkind="woocommerce",
        raw={"name": name, "slug": slug, "_loaded": {"name": name}},
    )


# -- tax rates ---------------------------------------------------------------------------------

_RATE_KEYS = (
    "name",
    "rate",
    "country",
    "state",
    "postcode",
    "city",
    "priority",
    "class",
    "compound",
    "shipping",
)
_RATE = re.compile(r"^\d+(\.\d{1,4})?$")


def rate_body(old: Mapping[str, Any], answers: Mapping[str, str]) -> dict[str, Any]:
    """A tax rate's changed fields (all of them for a new one), checked."""
    rate = answers.get("rate", "").strip()
    if rate and not _RATE.match(rate):
        raise ShopValueError("A tax rate is a percentage such as 8.25, with no percent sign.")
    country = answers.get("country", "").strip().upper()
    if country and not re.fullmatch(r"[A-Z]{2}", country):
        raise ShopValueError("A country is its two-letter code, such as US or GB.")
    wanted: dict[str, Any] = {
        "name": answers.get("name", "").strip(),
        "rate": rate,
        "country": country,
        "state": answers.get("state", "").strip().upper(),
        "postcode": answers.get("postcode", "").strip(),
        "city": answers.get("city", "").strip(),
    }
    if answers.get("class"):
        wanted["class"] = answers["class"]
    if not old:
        if not rate:
            raise ShopValueError("A new tax rate needs its percentage.")
        return wanted
    return {k: v for k, v in wanted.items() if str(old.get(k, "") or "") != str(v)}


def rate_preview(
    name: str, old: Mapping[str, Any], body: Mapping[str, Any], site: str
) -> list[str]:
    if not old:
        where = body.get("country") or "everywhere"
        return [
            f"A new tax rate on {site}: {body.get('name') or 'Tax'}, {body['rate']} percent, "
            f"{where}.",
            "WooCommerce charges it on the next order it applies to.",
        ]
    lines = [f"The tax rate {name} on {site}:"]
    lines += [
        f"{k.capitalize()}: {old.get(k) or 'blank'} becomes {v or 'blank'}."
        for k, v in body.items()
    ]
    lines.append("Past orders keep the tax they were charged.")
    return lines


# -- shipping locations ---------------------------------------------------------------------------


def location_body(text: str) -> list[dict[str, str]]:
    """``"country US, state US:AZ, postcode 85*"`` -> WooCommerce's locations, checked."""
    out = []
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        kind, _, code = part.partition(" ")
        kind, code = kind.strip().lower(), code.strip()
        if kind not in LOCATION_TYPES or not code:
            raise ShopValueError(
                f"{part} is not a location. Write a kind and a code, such as country US, "
                "state US:AZ, postcode 85001 or continent EU."
            )
        out.append({"code": code.upper() if kind != "postcode" else code, "type": kind})
    return out


# -- loading ------------------------------------------------------------------------------------


def _collection(api: Any, route: str, **params: Any) -> list[dict[str, Any]]:
    found = api.get(route, **params)
    return [r for r in found if isinstance(r, dict)] if isinstance(found, list) else []


def load_shop_setup(ctx: Any, what: str, query: Mapping[str, object]) -> list[WbRow]:
    """``reviews``, ``webhooks``, ``shipping``, ``taxes``, ``tax_classes``, ``attributes``,
    ``brands`` (the shop's index is checked by the caller)."""
    from quill.core.wordpress import workbench_shop_care as care

    api, site = ctx.api, ctx.name
    search = {"search": query["search"]} if query.get("search") else {}
    if what == "reviews":
        found = api.iter_collection(
            care.REVIEWS, {"status": "all", **search}, per_page=100, max_pages=3
        )
        return [care.review_row(r, site) for r in found if isinstance(r, dict)]
    if what == "webhooks":
        found = api.iter_collection(
            care.WEBHOOKS, {"status": "all", **search}, per_page=100, max_pages=2
        )
        return [care.webhook_row(r, site) for r in found if isinstance(r, dict)]
    if what == "shipping":
        rows = []
        for zone in _collection(api, ZONES):
            zid = zone.get("id", 0)
            locations = _collection(api, f"{ZONES}/{zid}/locations") if zid else []
            rows.append(zone_row(zone, locations, _collection(api, f"{ZONES}/{zid}/methods"), site))
        return rows
    if what == "taxes":
        found = api.iter_collection(TAXES, {}, per_page=100, max_pages=5)
        return [rate_row(r, site) for r in found if isinstance(r, dict)]
    if what == "tax_classes":
        return [tax_class_row(r, site) for r in _collection(api, TAX_CLASSES)]
    if what == "attributes":
        return [term_row("shop_attribute", r, site) for r in _collection(api, ATTRIBUTES)]
    try:
        found = list(api.iter_collection(BRANDS, dict(search), per_page=100, max_pages=3))
    except WordPressApiError as exc:
        if exc.status == 404:
            raise WordPressApiError(
                f"{site}'s WooCommerce does not list products/brands in its REST index, so it "
                "has no brands here. Brands came with WooCommerce 9.6."
            ) from exc
        raise
    return [term_row("shop_brand", r, site) for r in found if isinstance(r, dict)]
