"""The plugin screens of the wp-admin map (wordpress.md 9.18, package 14; wp_missing.md).

Split from :mod:`quill.core.wordpress.workbench_admin_map` (GATE-11), which
turns each row here into an :class:`~quill.core.wordpress.workbench_admin_map.AdminScreen`
and offers it only on a site whose REST index lists the plugin's namespace.
Each row is ``(key, path under wp-admin, name, nearest node, reach, says,
namespace)``, so **wp-admin for This Place** on Forms, Responses, Redirects,
the Shop's lists, the Events Calendar's lists and each Memberships node opens
the plugin's own screen for what REST cannot do there.

The ``admin.php?page=`` slugs are the plugins' own, as their admin menus
register them; the one that could not be checked against the plugin's source
says so beside it. Wx-free and network-free.
"""

from __future__ import annotations

__all__ = ["PLUGIN_SCREENS"]

_GF = "gf/v2"
_QAF = "qaf/v1"
_REDIRECTION = "redirection/v1"
_WC = "wc/v3"
_TEC = "tribe/events/v1"
_PMPRO = "pmpro/v1"

PLUGIN_SCREENS: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    # -- Gravity Forms --------------------------------------------------------------
    (
        "gf_forms",
        "admin.php?page=gf_edit_forms",
        "Forms > Forms",
        "forms",
        "both",
        "Building, settings, feeds and results are in Forms; the drag-and-drop editor, "
        "conditional logic beyond the supported fields, and add-on settings are in "
        "Gravity Forms' screens.",
        _GF,
    ),
    (
        "gf_entries",
        "admin.php?page=gf_entries",
        "Forms > Entries",
        "form_entries",
        "workbench",
        "Reading, starring, notes, answers, spam and resending notifications are in Responses.",
        _GF,
    ),
    (
        "gf_settings",
        "admin.php?page=gf_settings",
        "Forms > Settings",
        "forms",
        "dashboard",
        "Gravity Forms' own settings, its licence key and its add-ons are not in its REST routes.",
        _GF,
    ),
    # -- QUILL Accessible Forms ---------------------------------------------------------
    (
        "qaf_forms",
        # Unverified: the plugin's source is not in this repository, so this slug is the
        # menu's expected name rather than one read from its add_menu_page call.
        "admin.php?page=qaf",
        "Accessible Forms",
        "forms",
        "workbench",
        "Forms, publishing, settings, status, responses, views and spam are in Forms; "
        "wp-admin's screen shows the same forms.",
        _QAF,
    ),
    # -- Redirection --------------------------------------------------------------------
    (
        "redirection",
        "tools.php?page=redirection.php",
        "Tools > Redirection",
        "redirects",
        "both",
        "Adding, changing and removing redirects is in Redirects; groups and Redirection's "
        "options are in its own screens.",
        _REDIRECTION,
    ),
    (
        "redirection_404s",
        "tools.php?page=redirection.php&sub=404s",
        "Tools > Redirection > 404s",
        "not_found_log",
        "workbench",
        "The 404 log, and a redirect made from one of its addresses, are in 404 Log.",
        _REDIRECTION,
    ),
    # -- WooCommerce ----------------------------------------------------------------------
    (
        "wc_products",
        "edit.php?post_type=product",
        "Products > All Products",
        "shop",
        "both",
        "Listing, adding, prices, stock, status, categories and duplicating are in Shop; "
        "the rest of a product's fields are in WooCommerce's product screen.",
        _WC,
    ),
    (
        "wc_orders",
        # WooCommerce's own order screen since high-performance order storage; a site
        # still on the older storage redirects it to edit.php?post_type=shop_order.
        "admin.php?page=wc-orders",
        "WooCommerce > Orders",
        "shop_orders",
        "both",
        "Orders, their status, notes and refunds are in Shop Orders; making an order or "
        "changing its items and addresses is in WooCommerce's screen.",
        _WC,
    ),
    (
        "wc_reports",
        "admin.php?page=wc-admin&path=%2Fanalytics%2Foverview",
        "Analytics > Overview",
        "shop_reports",
        "both",
        "Sales, top sellers and order and customer totals are in Shop Reports; "
        "WooCommerce Analytics' own charts and date comparisons are in its screens.",
        _WC,
    ),
    (
        "wc_settings",
        "admin.php?page=wc-settings",
        "WooCommerce > Settings",
        "shop_settings",
        "both",
        "Store Settings reads every setting WooCommerce's REST routes carry, and Change "
        "Setting changes one after a preview. Password-style settings, such as a payment "
        "gateway's keys, are changed only in WooCommerce's screens.",
        _WC,
    ),
    (
        "wc_status",
        "admin.php?page=wc-status&tab=action-scheduler",
        "WooCommerce > Status > Scheduled Actions",
        "shop",
        "dashboard",
        "Scheduled Actions are not in WooCommerce's REST routes.",
        _WC,
    ),
    (
        "wc_extensions",
        "admin.php?page=wc-admin&path=%2Fextensions",
        "WooCommerce > Extensions",
        "shop",
        "dashboard",
        "The marketplace links a WooCommerce.com account; it is not a site-owner edit.",
        _WC,
    ),
    # -- The Events Calendar ------------------------------------------------------------
    (
        "events_list",
        "edit.php?post_type=tribe_events",
        "Events > Events",
        "events",
        "workbench",
        "Listing, filtering, adding, changing and trashing events are in Events Calendar.",
        _TEC,
    ),
    (
        "events_venues",
        "edit.php?post_type=tribe_venue",
        "Events > Venues",
        "events_venues",
        "workbench",
        "Venues are listed, added, changed and trashed in Venues.",
        _TEC,
    ),
    (
        "events_organizers",
        "edit.php?post_type=tribe_organizer",
        "Events > Organizers",
        "events_organizers",
        "workbench",
        "Organizers are listed, added, changed and trashed in Organizers.",
        _TEC,
    ),
    (
        "events_categories",
        "edit-tags.php?taxonomy=tribe_events_cat&post_type=tribe_events",
        "Events > Event Categories",
        "events_categories",
        "workbench",
        "Event categories are listed and changed in Event Categories.",
        _TEC,
    ),
    (
        "events_settings",
        "edit.php?post_type=tribe_events&page=tec-events-settings",
        "Events > Settings",
        "events",
        "dashboard",
        "The Events Calendar's settings are not in its REST routes.",
        _TEC,
    ),
    (
        "events_import",
        "edit.php?post_type=tribe_events&page=aggregator",
        "Events > Import",
        "events",
        "dashboard",
        "Event Aggregator's importers are not in REST.",
        _TEC,
    ),
    # -- Yoast SEO ------------------------------------------------------------------------
    (
        "yoast_settings",
        "admin.php?page=wpseo_page_settings",
        "Yoast SEO > Settings",
        "settings",
        "dashboard",
        "Yoast's full settings, redirects, schema and breadcrumbs are in its own screens.",
        "yoast/v1",
    ),
    # -- Paid Memberships Pro -------------------------------------------------------------
    (
        "pmpro_dashboard",
        "admin.php?page=pmpro-dashboard",
        "Memberships > Dashboard",
        "memberships",
        "both",
        "Levels, orders, subscriptions and discount codes are in Memberships; reports and "
        "settings are in Paid Memberships Pro's screens.",
        _PMPRO,
    ),
    (
        "pmpro_levels",
        "admin.php?page=pmpro-membershiplevels",
        "Memberships > Settings > Levels",
        "membership_levels",
        "both",
        "Levels are read in Membership Levels; making or changing a level, its price and "
        "its content restrictions is in Paid Memberships Pro's screen.",
        _PMPRO,
    ),
    (
        "pmpro_members",
        "admin.php?page=pmpro-memberslist",
        "Memberships > Members",
        "memberships",
        "both",
        "A member's levels are on their People row, and Change Membership and Cancel "
        "Membership are there; the full members list and its export are in wp-admin.",
        _PMPRO,
    ),
    (
        "pmpro_orders",
        "admin.php?page=pmpro-orders",
        "Memberships > Orders",
        "membership_orders",
        "both",
        "Orders are read in Orders; editing an order or refunding one is in Paid "
        "Memberships Pro's screen.",
        _PMPRO,
    ),
    (
        "pmpro_discount_codes",
        "admin.php?page=pmpro-discountcodes",
        "Memberships > Discount Codes",
        "membership_discount_codes",
        "both",
        "Codes are looked up and made in Discount Codes; changing or deleting one is in "
        "Paid Memberships Pro's screen.",
        _PMPRO,
    ),
    (
        "pmpro_reports",
        "admin.php?page=pmpro-reports",
        "Memberships > Reports",
        "memberships",
        "dashboard",
        "Paid Memberships Pro's reports (sales, sign-ups, cancellations, visits) are not in "
        "its REST routes.",
        _PMPRO,
    ),
    (
        "pmpro_settings",
        "admin.php?page=pmpro-paymentsettings",
        "Memberships > Settings > Payment Gateway",
        "memberships",
        "dashboard",
        "Paid Memberships Pro's settings (pages, payment gateway, email and advanced) are "
        "not in its REST routes.",
        _PMPRO,
    ),
)
"""Plugin screens, plugin by plugin, each with the namespace that offers it."""
