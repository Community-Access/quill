"""The Workbench's nodes for WooCommerce, The Events Calendar and Yoast SEO (wordpress.md 19, 8-12).

Spliced into the site template by :data:`quill.core.wordpress.workbench_shop.SHOP_NODES`
(the tree itself is at its size budget). Each node's loader is answered by
:func:`quill.core.wordpress.workbench_shop.load_shop`, and each node and row
kind has its F1 sentence here, which :mod:`quill.core.wordpress.workbench_node_help`
splices in. A filter node shares its parent's loader with a preset, so it is
never a loader's home (the tree's "nothing dropped" count). Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping

from quill.core.workbench.tree import NodeSpec

__all__ = ["PLUGIN_NODES", "PLUGIN_NODE_HELP", "PLUGIN_ROW_HELP", "SHOP_FILTER_NODES"]

_PRODUCT_COLUMNS = ("name", "price", "stock", "status")

SHOP_FILTER_NODES: tuple[NodeSpec, ...] = (
    NodeSpec(
        "shop_drafts",
        "Draft Products",
        "shop",
        loader="shop:products",
        preset=(("status", "draft"),),
        columns=_PRODUCT_COLUMNS,
        row_type="shop_product",
        home=False,
    ),
    NodeSpec(
        "shop_on_sale",
        "On Sale",
        "shop",
        loader="shop:products",
        preset=(("on_sale", "true"),),
        columns=_PRODUCT_COLUMNS,
        row_type="shop_product",
        home=False,
    ),
    NodeSpec(
        "shop_out_of_stock",
        "Out of Stock",
        "shop",
        loader="shop:products",
        preset=(("stock_status", "outofstock"),),
        columns=_PRODUCT_COLUMNS,
        row_type="shop_product",
        home=False,
    ),
)
"""Shop's own filters, as WooCommerce's products route takes them (Package 8)."""

PLUGIN_NODES: tuple[NodeSpec, ...] = (
    *SHOP_FILTER_NODES,
    NodeSpec(
        "shop_customers",
        "Customers",
        "shop",
        loader="shop:customers",
        columns=("name", "username", "registered", "paying"),
        row_type="shop_customer",
    ),
    NodeSpec(
        "shop_coupons",
        "Coupons",
        "shop",
        loader="shop:coupons",
        columns=("code", "discount", "used", "expires"),
        row_type="shop_coupon",
    ),
    NodeSpec(
        "shop_reports",
        "Shop Reports",
        "shop",
        loader="shop:reports",
        columns=("report", "says"),
        row_type="shop_report",
    ),
    NodeSpec(
        "shop_settings",
        "Store Settings",
        "shop",
        loader="shop:settings",
        columns=("group", "setting", "value"),
        row_type="shop_setting",
    ),
    *(
        NodeSpec(key, label, "shop", loader=f"shop:{what}", columns=columns, row_type=kind)
        for key, label, what, columns, kind in (
            (
                "shop_reviews",
                "Product Reviews",
                "reviews",
                ("product", "rating", "reviewer", "status", "date"),
                "shop_review",
            ),
            (
                "shop_shipping",
                "Shipping Zones",
                "shipping",
                ("zone", "locations", "methods"),
                "shop_zone",
            ),
            (
                "shop_taxes",
                "Tax Rates",
                "taxes",
                ("name", "rate", "where", "class"),
                "shop_tax_rate",
            ),
            ("shop_tax_classes", "Tax Classes", "tax_classes", ("name", "slug"), "shop_tax_class"),
            ("shop_attributes", "Attributes", "attributes", ("name", "slug"), "shop_attribute"),
            ("shop_brands", "Brands", "brands", ("name", "slug", "products"), "shop_brand"),
            (
                "shop_webhooks",
                "Webhooks",
                "webhooks",
                ("name", "topic", "status", "delivery"),
                "shop_webhook",
            ),
        )
    ),
    NodeSpec(
        "events",
        "Events Calendar",
        "site",
        loader="events:upcoming",
        columns=("title", "when", "venue", "status"),
        row_type="tribe_event",
    ),
    NodeSpec(
        "events_past",
        "Past Events",
        "events",
        loader="events:past",
        columns=("title", "when", "venue", "status"),
        row_type="tribe_event",
    ),
    NodeSpec(
        "events_venues",
        "Venues",
        "events",
        loader="events:venues",
        columns=("name", "where", "phone"),
        row_type="tribe_venue",
    ),
    NodeSpec(
        "events_organizers",
        "Organizers",
        "events",
        loader="events:organizers",
        columns=("name", "phone", "website"),
        row_type="tribe_organizer",
    ),
    NodeSpec(
        "events_categories",
        "Event Categories",
        "events",
        loader="events:categories",
        columns=("name", "slug", "events"),
        row_type="tribe_category",
    ),
    NodeSpec(
        "events_tags",
        "Event Tags",
        "events",
        loader="events:tags",
        columns=("name", "slug", "events"),
        row_type="tribe_tag",
    ),
    NodeSpec(
        "seo",
        "SEO",
        "site",
        loader="seo:items",
        columns=("title", "seo_title", "description", "index", "keyphrase"),
        row_type="seo_item",
    ),
    NodeSpec(
        "seo_site",
        "Site SEO",
        "seo",
        loader="seo:site",
        columns=("what", "says"),
        row_type="seo_score",
    ),
)
"""Below Shop: its filters, Customers, Coupons, Reports and Store Settings; then Events and SEO."""

PLUGIN_NODE_HELP: Mapping[str, str] = {
    "shop_drafts": "WooCommerce products still in draft. Enter opens one on the site.",
    "shop_on_sale": "WooCommerce products with a sale price in effect now.",
    "shop_out_of_stock": "WooCommerce products WooCommerce says are out of stock.",
    "shop_customers": (
        "WooCommerce's customers: name, username, when they joined and whether they have "
        "paid. Email and addresses stay out of the list; Customer Details reads them."
    ),
    "shop_coupons": (
        "WooCommerce's coupons. Ctrl+N makes one, Edit Coupon changes one, and Delete "
        "moves one to the Trash, each after a preview."
    ),
    "shop_reports": (
        "WooCommerce's reports as sentences, each with its small table in the details: "
        "sales this month, top sellers, and orders, products, customers, coupons and "
        "reviews by kind."
    ),
    "shop_settings": (
        "WooCommerce > Settings, read from its settings groups. Change Setting previews the "
        "old and new value first; a password-style setting is never read aloud or changed here."
    ),
    "events": (
        "The Events Calendar's events from now on, soonest first, through tribe/events/v1. "
        "Ctrl+N makes one; times are in each event's own time zone, and yours is said too."
    ),
    "events_past": "Events that have ended, newest first.",
    "events_venues": "The Events Calendar's venues. Ctrl+N makes one; Delete trashes one.",
    "events_organizers": (
        "The Events Calendar's organizers. Ctrl+N makes one; Delete moves one to the Trash."
    ),
    "seo": (
        "Yoast SEO for the newest posts and pages: the title and description search engines "
        "are given, whether it is indexed, and its focus keyphrase. Edit SEO changes them."
    ),
    "shop_reviews": (
        "WooCommerce's product reviews, every status. Approve, Hold and Mark as Spam work on a "
        "selection and say how each went; Reply answers under a review; Delete moves to the "
        "Trash. A reviewer's email is never shown."
    ),
    "shop_shipping": (
        "WooCommerce's shipping zones, each with its locations and methods. Ctrl+N makes a "
        "zone; Locations and Methods change them, each after a preview."
    ),
    "shop_taxes": "WooCommerce's tax rates. Ctrl+N makes one; Edit Tax Rate changes one.",
    "shop_tax_classes": (
        "WooCommerce's tax classes. Ctrl+N makes one; deleting one deletes its rates."
    ),
    "shop_attributes": (
        "WooCommerce's product attributes, such as Size. Terms changes their values; Ctrl+N "
        "makes one."
    ),
    "shop_brands": (
        "WooCommerce's brands, on a site whose WooCommerce has them (9.6 and later). Ctrl+N "
        "makes one."
    ),
    "shop_webhooks": (
        "WooCommerce's webhooks: what each sends, where, and whether it is paused. Ctrl+N "
        "makes one; its secret is made by WooCommerce and never shown."
    ),
    "events_categories": (
        "The Events Calendar's event categories, with how many events use each. Ctrl+N "
        "makes one; Categories and Tags on an event gives it some."
    ),
    "events_tags": "The Events Calendar's event tags. Ctrl+N makes one.",
    "seo_site": (
        "Yoast SEO for the whole site: its SEO and readability scores, and what only "
        "Yoast's own screens in wp-admin can do, each opened with Enter."
    ),
}
"""One F1 sentence per node above."""

PLUGIN_ROW_HELP: Mapping[str, str] = {
    "shop_product": (
        "A WooCommerce product. Enter opens it on the site; the context menu edits its price, "
        "stock, status and categories, reads and edits its variations, duplicates it, and "
        "Delete moves it to the Trash, each after a preview."
    ),
    "shop_order": (
        "A WooCommerce shop order. Not a membership order. The context menu changes its "
        "status, reads and adds notes, and makes a refund, which moves money and asks you "
        "to type the amount first."
    ),
    "shop_customer": (
        "A WooCommerce customer. Customer Details reads their email and addresses, and Edit "
        "Customer changes them, for a role WooCommerce lets do so; the list never shows them."
    ),
    "shop_coupon": "A WooCommerce coupon. Edit Coupon changes it, previewed; Delete trashes it.",
    "shop_report": "One WooCommerce report as a sentence; Enter reads its table.",
    "shop_setting": "One WooCommerce setting. Change Setting previews the old and new value.",
    "tribe_event": (
        "An event in The Events Calendar. Edit Event changes it after a preview; Delete moves "
        "it to the Trash; Categories and Tags sets its terms. A recurring event says so and "
        "is changed in wp-admin."
    ),
    "tribe_venue": "A venue in The Events Calendar. Edit Venue changes it; Delete trashes it.",
    "tribe_organizer": (
        "An organizer in The Events Calendar. Edit Organizer changes it; Delete trashes it."
    ),
    "seo_item": (
        "A post or page with its Yoast SEO. Search Appearance reads what a search engine "
        "shows; Edit SEO changes the title, description, keyphrase, indexing and social "
        "title, description and image; the Bulk SEO Editor changes many in one window."
    ),
    "shop_review": (
        "A WooCommerce product review. Approve, Hold, Mark as Spam, Reply, Edit Review and "
        "Delete (to the Trash) are on its context menu, each after a preview; Ctrl+Z undoes."
    ),
    "shop_zone": "A shipping zone. Locations and Methods change it; Delete removes it for good.",
    "shop_tax_rate": "A tax rate. Edit Tax Rate changes it; a deleted one comes back with Ctrl+Z.",
    "shop_tax_class": "A tax class. Delete removes it and every rate in it, for good.",
    "shop_webhook": (
        "A WooCommerce webhook. Pause or Activate stops or starts it; its secret is never shown."
    ),
    "shop_attribute": "A product attribute. Terms changes its values; Rename and Delete too.",
    "shop_brand": "A WooCommerce brand. Rename changes it; Delete removes it for good.",
    "tribe_category": "An event category. Rename changes it; Delete removes it for good.",
    "tribe_tag": "An event tag. Rename changes it; Delete removes it for good.",
    "seo_score": "A Yoast SEO score for the site, or a job only wp-admin does; Enter opens it.",
}
"""One F1 sentence per row kind these nodes hold (the two shop kinds replace their old words)."""
