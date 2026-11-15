"""The covered-route table of :mod:`quill.core.wordpress.workbench_coverage`.

Split out to keep that module under its size budget (GATE-11). Each entry is a
pattern on a REST path (no leading slash) and where the Workbench reaches it.
Pure data: wx-free and network-free.
"""

from __future__ import annotations

__all__ = ["COVERED"]


# (pattern on the path without its leading slash, home) for routes with a built home.
COVERED: tuple[tuple[str, str], ...] = (
    (r"$", "the site's Overview, from its index"),
    (r"batch/v1$", "batch edits: Properties on several rows"),
    (
        r"quill-site-types/v1(/.*)?$",
        "Sites > site > Content Model: Define with QUILL Site Types, Stop Defining, Export as Code",
    ),
    (r"wp/v2/(posts|pages)(/.*)?$", "Sites > site > Posts and Pages"),
    (r"wp/v2/media(/.*)?$", "Sites > site > Media"),
    (r"wp/v2/comments(/.*)?$", "Sites > site > Comments"),
    (r"wp/v2/(categories|tags)(/.*)?$", "Sites > site > Categories and Tags"),
    (r"wp/v2/users(/.*)?$", "Sites > site > People > Users and Application Passwords"),
    (
        r"wp/v2/plugins(/.*)?$",
        "Sites > site > Plugins (install, activate, deactivate, delete; updates in wp-admin)",
    ),
    (
        r"wp/v2/themes(/.*)?$",
        "Sites > site > Appearance > Themes (read only; the rest in wp-admin)",
    ),
    (r"wp/v2/settings$", "Sites > site > Settings"),
    (r"wp/v2/(menus|menu-items|menu-locations)(/.*)?$", "Sites > site > Menus and Navigation"),
    (r"wp/v2/navigation(/.*)?$", "Sites > site > Menus and Navigation"),
    (r"wp/v2/(templates|template-parts)(/.*)?$", "Sites > site > Appearance > Templates"),
    (r"wp/v2/blocks(/.*)?$", "Sites > site > Appearance > Patterns"),
    (r"wp/v2/(font-families|font-collections)(/.*)?$", "Sites > site > Appearance > Fonts"),
    (r"wp/v2/(sidebars|widgets|widget-types)(/.*)?$", "Sites > site > Appearance > Widgets"),
    (r"wp/v2/(types|taxonomies|statuses)(/.*)?$", "Sites > site > Content Model"),
    (r"wp/v2/search$", "Search, across every site"),
    (r"wp/v2/global-styles(/.*)?$", "Sites > site > Appearance > Global Styles"),
    (
        r"wp/v2/(block-types|block-patterns|block-renderer|pattern-directory)(/.*)?$",
        "the editor's block commands",
    ),
    (r"wp/v2/block-directory(/.*)?$", "the editor's block commands"),
    (
        r"wp/v2/[a-z0-9_-]+/\(\?P<parent>[^)]*\)/(revisions|autosaves)(/.*)?$",
        "File > WordPress > Previous Versions, in the editor",
    ),
    (r"wp/v2/wp_pattern_category(/.*)?$", "Sites > site > Appearance > Patterns"),
    (r"wp-site-health/v1(/.*)?$", "Sites > site > Site Health"),
    (r"wp-abilities/v1(/.*)?$", "Sites > site > Abilities"),
    (r"wp-block-editor/v1(/.*)?$", "the editor's link and image commands"),
    (r"oembed/1\.0(/embed)?$", "the editor's Insert Link, for embeds"),
    (r"(baf|qaf)/v1/(forms|entries)(/.*)?$", "Sites > site > Forms"),
    (r"(baf|qaf)/v1/spam$", "Sites > site > Properties, the Spam page"),
    (r"(baf|qaf)/v1/spam/weeks$", "a site's Form Spam by Week, its Spam page and the weekly Watch"),
    (r"(baf|qaf)/v1/spam/questions(/.*)?$", "a site's Form Spam Questions"),
    (r"gf/v2/feeds(/.*)?$", "Sites > site > Forms > Feeds"),
    (r"gf/v2/forms/[^/]+/feeds$", "Sites > site > Forms > Feeds"),
    (r"gf/v2/forms/[^/]+/results$", "Sites > site > Forms > Results"),
    (r"gf/v2/forms/[^/]+/field-filters$", "Sites > site > Forms > Responses, Filter Builder"),
    (r"gf/v2/forms/[^/]+/submissions(/validation)?$", "a Gravity Forms form's Test This Form"),
    (r"gf/v2/entries/[^/]+/(notes|notifications)$", "a Gravity Forms entry's context menu"),
    (r"gf/v2/notes(/.*)?$", "a Gravity Forms entry's Notes"),
    (
        r"gf/v2/forms(/[^/]+)?$",
        "Sites > site > Forms: New Gravity Form and Edit Form (QUILL's form editor)",
    ),
    (r"gf/v2/(forms|entries)(/.*)?$", "Sites > site > Forms"),
    (r"pmpro/v1/discount_code(/.*)?$", "Sites > site > Memberships > Discount Codes"),
    (r"pmpro/v1/has_membership_access$", "Users > person > Check Membership Access"),
    (
        r"pmpro/v1/(change|cancel)_membership_level$",
        "Users > person > Change Membership Level and Cancel Membership, previewed every run",
    ),
    (
        r"pmpro/v1/get_membership_levels?_for_user$",
        "Users > person > Show Memberships, where the site has no PMPro abilities",
    ),
    (r"redirection/v1/(redirect|404)(/.*)?$", "Sites > site > Redirects and its 404 Log"),
    (r"redirection/v1/bulk/redirect(/.*)?$", "Sites > site > Redirects (on, off, delete)"),
    # Packages 8 to 13 (2026-11-13): WooCommerce, The Events Calendar and Yoast SEO.
    (r"wc/v3/products(/\(\?P<id>[^)]*\))?$", "Sites > site > Shop: list, new, edit, trash"),
    (r"wc/v3/products/\(\?P<id>[^)]*\)/duplicate$", "a Shop product's Duplicate"),
    (r"wc/v3/products/\(\?P<product_id>[^)]*\)/variations$", "Shop > Show Its Variations"),
    (r"wc/v3/products/categories$", "a Shop product's Edit Product, its categories"),
    (r"wc/v3/orders(/\(\?P<id>[^)]*\))?$", "Sites > site > Shop > Shop Orders, Change Status"),
    (r"wc/v3/orders/\(\?P<order_id>[^)]*\)/(notes|refunds)$", "a shop order's Notes, Refund"),
    (r"wc/v3/coupons(/\(\?P<id>[^)]*\))?$", "Sites > site > Shop > Coupons"),
    (r"wc/v3/customers$", "Sites > site > Shop > Customers, read only"),
    (r"wc/v3/reports/(sales|top_sellers|[a-z]+/totals)$", "Sites > site > Shop > Shop Reports"),
    (r"wc/v3/data/currencies/current$", "Sites > site > Shop > Shop Reports, the currency"),
    (r"wc/v3/settings(/\(\?P<group_id>[^)]*\))?$", "Sites > site > Shop > Store Settings"),
    (
        r"wc/v3/settings/\(\?P<group_id>[^)]*\)/\(\?P<id>[^)]*\)$",
        "Store Settings > Change Setting, previewed",
    ),
    (
        r"tribe/events/v1/(events|venues|organizers)(/\(\?P<id>[^)]*\))?$",
        "Sites > site > Events Calendar, its Venues and Organizers",
    ),
    (r"yoast/v1/(seo_scores|readability_scores)$", "Sites > site > SEO > Site SEO"),
    # 2026-11-14: the Packages 8 to 13 leftovers that were still wp-admin.
    (
        r"wc/v3/products/reviews(/\(\?P<[a-z_]*id>[^)]*\))?$",
        "Sites > site > Shop > Product Reviews",
    ),
    (
        r"wc/v3/shipping/zones(/\(\?P<[a-z_]*id>[^)]*\)(/locations|/methods(/\(\?P<[a-z_]*id>[^)]*\))?)?)?$",
        "Sites > site > Shop > Shipping Zones, Locations and Methods",
    ),
    (r"wc/v3/taxes(/\(\?P<[a-z_]*id>[^)]*\))?$", "Sites > site > Shop > Tax Rates"),
    (r"wc/v3/taxes/classes(/\(\?P<slug>[^)]*\))?$", "Sites > site > Shop > Tax Classes"),
    (r"wc/v3/webhooks(/\(\?P<[a-z_]*id>[^)]*\))?$", "Sites > site > Shop > Webhooks"),
    (
        r"wc/v3/products/attributes(/\(\?P<[a-z_]*id>[^)]*\)(/terms(/\(\?P<[a-z_]*id>[^)]*\))?)?)?$",
        "Sites > site > Shop > Attributes and their Terms",
    ),
    (r"wc/v3/products/brands(/\(\?P<[a-z_]*id>[^)]*\))?$", "Sites > site > Shop > Brands"),
    (
        r"wc/v3/customers/\(\?P<[a-z_]*id>[^)]*\)$",
        "a Shop customer's Customer Details and Edit Customer",
    ),
    (
        r"wc/v3/products/\(\?P<[a-z_]*id>[^)]*\)/variations/\(\?P<[a-z_]*id>[^)]*\)$",
        "a Shop product's Edit a Variation",
    ),
    (
        r"tribe/events/v1/(categories|tags)(/\(\?P<[a-z_]*id>[^)]*\))?$",
        "Sites > site > Events Calendar > Event Categories and Event Tags",
    ),
    (
        r"yoast/v1/bulk_editor/(posts|update_search|update_social)$",
        "SEO > Bulk SEO Editor, and Edit SEO where Yoast registers no meta",
    ),
    (r"(baf|qaf)/v1/views$", "Sites > site > Forms, a form's Saved Views"),
)
