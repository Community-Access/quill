"""The Workbench's Shop, Shop Orders and Podcast nodes, from the routes the site offers (WP-A).

**Shop** is WooCommerce's ``wc/v3``: the products, and under them **Shop
Orders**, Customers, Coupons, Shop Reports and Store Settings
(:mod:`quill.core.wordpress.workbench_plugin_nodes`); what can be changed is
in :mod:`~quill.core.wordpress.workbench_shop_catalog`,
:mod:`~quill.core.wordpress.workbench_shop_orders` and
:mod:`~quill.core.wordpress.workbench_shop_settings`, each after a preview.
The Events Calendar and Yoast SEO nodes are spliced here too and loaded by
:func:`load_shop`. A site whose REST index has no ``wc/v3`` is told so in
one sentence, not shown an empty list. A shop order is never a membership
order: Paid Memberships Pro's orders are under Needs My Attention >
Membership Orders and Memberships > Orders, and every shop row says which it
is. Orders hold customers' names and addresses, so a shop order row keeps only
what reading it as a receipt needs (no email, telephone or billing address).

**Podcast** is the site's episodes. A content type the site describes as a
podcast or its episodes (``wp/v2/types``, the way Seriously Simple Podcasting
registers one) is listed as its items; otherwise an episode is a post that
carries an episode's player, the shape QUILL Cast's Post This Episode makes
(:func:`quill.core.wordpress.episode.is_episode_post`). A site with neither
is told so.

Wx-free; every request goes through the site's own client.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress import episode as ep
from quill.core.wordpress import site_types as stypes
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, Order, order_from
from quill.core.wordpress.site import friendly_date, raw_text
from quill.core.wordpress.workbench_listing import pages_for
from quill.core.wordpress.workbench_plugin_nodes import PLUGIN_NODES
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.tree import NodeSpec

__all__ = [
    "MEMBERSHIP_NOT_SHOP",
    "PODCAST_WORDS",
    "SHOP_NODES",
    "has_shop",
    "load_episodes",
    "load_shop",
    "load_shop_orders",
    "load_shop_products",
    "no_shop_words",
    "podcast_type",
    "shop_order_row",
]

_PER_PAGE = 100
_PAGES = 3

SHOP_NODES: tuple[NodeSpec, ...] = (
    NodeSpec(
        "shop",
        "Shop",
        "site",
        loader="shop:products",
        columns=("name", "price", "stock", "status"),
        row_type="shop_product",
    ),
    NodeSpec(
        "shop_orders",
        "Shop Orders",
        "shop",
        loader="shop:orders",
        columns=("what", "status", "customer", "total", "date"),
        row_type="shop_order",
    ),
    NodeSpec(
        "podcast",
        "Podcast",
        "site",
        loader="podcast:episodes",
        columns=("title", "status", "author", "modified"),
        row_type="item",
    ),
    *PLUGIN_NODES,
)
"""The site template's Shop, Shop Orders and Podcast nodes, then Shop's other nodes, Events
Calendar and SEO (the tree splices them)."""

MEMBERSHIP_NOT_SHOP = (
    "A WooCommerce shop order. Membership orders from Paid Memberships Pro "
    "are a different thing, under Needs My Attention > Membership Orders and Memberships > "
    "Orders."
)
"""Said in every shop order, so the two kinds of order are never confused."""

PODCAST_WORDS = ("podcast", "episode")
"""A content type is the podcast's when its slug, REST base or name says one of these."""


def _namespaces(ctx: Any) -> tuple[str, ...]:
    info = getattr(ctx, "info", None)
    return tuple(getattr(info, "namespaces", ()) or ())


def has_shop(ctx: Any) -> bool:
    """Whether the site's REST index lists WooCommerce's ``wc/v3``."""
    return SHOP_NAMESPACE in _namespaces(ctx)


def no_shop_words(site: str) -> str:
    return (
        f"{site} does not list WooCommerce's {SHOP_NAMESPACE} routes in its REST index, so it "
        "has no shop QUILL can read. Membership orders from Paid Memberships Pro are under "
        "Needs My Attention > Membership Orders."
    )


def _collect(ctx: Any, route: str, params: Mapping[str, object]) -> list[dict[str, Any]]:
    try:
        found = ctx.api.iter_collection(
            route, dict(params), per_page=_PER_PAGE, max_pages=pages_for(_PAGES)
        )
        return [r for r in found if isinstance(r, dict)]
    except WordPressApiError as exc:
        if exc.status in (401, 403):
            raise WordPressApiError(
                f"{ctx.name} lets only shop managers read its shop, and your role there "
                "cannot. WooCommerce asks for the manage_woocommerce capability.",
                status=exc.status,
            ) from exc
        raise


# -- products --------------------------------------------------------------------


def load_shop_products(ctx: Any, query: Mapping[str, object] | None = None) -> list[WbRow]:
    from quill.core.wordpress.workbench_shop_catalog import product_params, product_row

    if not has_shop(ctx):
        raise WordPressApiError(no_shop_words(ctx.name))
    raw = _collect(ctx, f"{SHOP_NAMESPACE}/products", product_params(dict(query or {})))
    return [product_row(r, ctx.name) for r in raw]


# -- orders ------------------------------------------------------------------------


def shop_order_row(order: Order, site: str, site_url: str = "") -> WbRow:
    """One WooCommerce order, as a receipt: no email, telephone or billing address."""
    status = order.status.replace("-", " ")
    total = f"{order.total} {order.currency}".strip()
    when = friendly_date(order.created) if order.created else ""
    link = (
        f"{site_url.rstrip('/')}/wp-admin/post.php?post={order.id}&action=edit"
        if site_url and order.id
        else ""
    )
    return WbRow(
        kind="shop_order",
        site=site,
        key=str(order.id),
        cells={
            "what": f"Shop order {order.number}",
            "status": status,
            "customer": order.customer or "a guest",
            "total": total,
            "date": when,
            "site": site,
        },
        detail=f"{order.spoken()}. {MEMBERSHIP_NOT_SHOP}",
        link=link,
        status=order.status,
        subkind="woocommerce",
        raw={
            "order": order.number,
            "kind_of_order": "WooCommerce shop order (not a membership order)",
            "status": status,
            "total": total,
            "customer": order.customer or "a guest",
            "placed": when,
            "items": order.details(),
        },
    )


def load_shop_orders(ctx: Any, query: Mapping[str, object] | None = None) -> list[WbRow]:
    if not has_shop(ctx):
        raise WordPressApiError(no_shop_words(ctx.name))
    params = {"orderby": "date", "order": "desc", **dict(query or {})}
    raw = _collect(ctx, f"{SHOP_NAMESPACE}/orders", params)
    return [shop_order_row(order_from(r), ctx.name, getattr(ctx, "url", "")) for r in raw]


# -- the podcast -------------------------------------------------------------------


def podcast_type(api: Any) -> stypes.WritingType | None:
    """The content type the site describes as its podcast or episodes, if it has one."""
    for found in stypes.discover_writing_types(api):
        words = f"{found.slug} {found.rest_base} {found.name}".casefold()
        if any(word in words for word in PODCAST_WORDS):
            return found
    return None


def load_episodes(ctx: Any, query: Mapping[str, object] | None = None) -> list[WbRow]:
    """The site's episodes: its podcast type's items, or its posts with an episode's player."""
    from quill.core.wordpress.workbench_load import load_items

    found = podcast_type(ctx.api)
    if found is not None:
        return load_items(ctx, found.kind, {"status": "any"}, dict(query or {}))
    posts = load_items(ctx, "post", {"status": "any"}, dict(query or {}))
    episodes = [row for row in posts if ep.is_episode_post(raw_text(row.raw.get("content")))]
    if not episodes and not query:
        raise WordPressApiError(
            f"{ctx.name} has no podcast here: no content type for a podcast or its episodes in "
            f"its REST index, and none of its newest {len(posts)} posts carries an episode's "
            "player. QUILL Cast's Episode > Post This Episode to WordPress makes one."
        )
    return episodes


def load_shop(ctx: Any, family: str, what: str, query: Mapping[str, object]) -> list[WbRow]:
    """The rows for a ``shop:``, ``podcast:``, ``events:`` or ``seo:`` loader."""
    if family == "podcast":
        return load_episodes(ctx, query)
    if family == "events":
        from quill.core.wordpress.workbench_events import load_events

        return load_events(ctx, what, query)
    if family == "seo":
        from quill.core.wordpress import workbench_seo as seo

        return seo.load_seo_site(ctx) if what == "site" else seo.load_seo_items(ctx, query)
    if what == "orders":
        return load_shop_orders(ctx, query)
    if what in ("customers", "coupons", "reports", "settings"):
        return _load_shop_more(ctx, what, query)
    if what in _SETUP:
        from quill.core.wordpress.workbench_shop_setup import load_shop_setup

        if not has_shop(ctx):
            raise WordPressApiError(no_shop_words(ctx.name))
        return load_shop_setup(ctx, what, query)
    return load_shop_products(ctx, query)


_SETUP = frozenset({
    "reviews",
    "webhooks",
    "shipping",
    "taxes",
    "tax_classes",
    "attributes",
    "brands",
})


def _load_shop_more(ctx: Any, what: str, query: Mapping[str, object]) -> list[WbRow]:
    """Customers, Coupons, Shop Reports and Store Settings (Packages 9 and 10)."""
    from quill.core.wordpress.workbench_shop_orders import coupon_row
    from quill.core.wordpress.workbench_shop_reports import customer_row, report_rows
    from quill.core.wordpress.workbench_shop_settings import load_settings_rows

    if not has_shop(ctx):
        raise WordPressApiError(no_shop_words(ctx.name))
    search = {"search": query["search"]} if query.get("search") else {}
    if what == "customers":
        found = _collect(ctx, f"{SHOP_NAMESPACE}/customers", {"role": "all", **search})
        return [customer_row(r, ctx.name) for r in found]
    if what == "coupons":
        found = _collect(ctx, f"{SHOP_NAMESPACE}/coupons", search)
        return [coupon_row(r, ctx.name) for r in found]
    if what == "reports":
        return report_rows(ctx.api, ctx.name)
    return load_settings_rows(ctx.api, ctx.name)
