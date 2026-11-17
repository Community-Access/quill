"""Every route a site offers, and where the WordPress Workbench reaches it (PRD 12).

Each route of a site's REST index is one of five things, decided by rule
from its path and methods (:func:`classify`):

- ``covered``: a node, sheet or command is built for it, named as its home;
- ``schema_built``: nothing was written for it, and it is usable anyway,
  because the Workbench builds its node, list and sheet from what the site
  says about it (a custom post type or taxonomy under ``wp/v2``, or any
  readable route under More from This Site);
- ``planned``: a home is planned (the Shop, Events, SEO and so on), named;
- ``wp_admin_only``: something only wp-admin does (a connection handshake,
  a setup wizard), with the screen it opens;
- ``out_of_scope``: for visitors or machines, not for running a site (a
  shopper's cart, an embed proxy, telemetry), with why.

The gate (:mod:`quill.tools.wordpress_coverage_audit`) runs this over the
test site's recorded index and compares it with a committed snapshot, so a
route that appears is ``missing`` until somebody looks at it, and a route
whose classification changed shows in the diff. The same rules label the
routes listed under More from This Site, so what the gate counts is what a
person sees. Wx-free and network-free.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from quill.core.wordpress.workbench_coverage_routes import COVERED
from quill.core.workbench.coverage import CoverageRow, CoverageStatus, CoverageTable

__all__ = [
    "NO_ROUTE",
    "STATUSES",
    "THIRD_SWEEP",
    "RouteClass",
    "SweepArea",
    "classify",
    "classify_index",
    "coverage_table",
    "namespace_of",
    "status_words",
    "summary",
    "sweep_disposition",
]

STATUSES = ("covered", "schema_built", "planned", "wp_admin_only", "out_of_scope")


@dataclass(frozen=True)
class RouteClass:
    """Where one route lives: its status and its home (a node, command, screen or reason)."""

    status: str
    home: str


def namespace_of(route: str, namespaces: Iterable[str]) -> str:
    """The longest of *namespaces* that *route* sits in (``/wp/v2/posts`` is in ``wp/v2``)."""
    path = route.strip("/")
    best = ""
    for namespace in namespaces:
        clean = namespace.strip("/")
        if (path == clean or path.startswith(f"{clean}/")) and len(clean) > len(best):
            best = clean
    return best or (path.split("/", 1)[0] if path else "(index)")


_COVERED = COVERED  # (pattern, home) for routes with a built home: workbench_coverage_routes

_WP_ADMIN: tuple[tuple[str, str], ...] = (
    (r"jetpack/v4/(connection|remote_|verify_|user-token|heartbeat).*", "Jetpack > Connection"),
    (r"wc-admin/onboarding.*", "WooCommerce > Home, the setup tasks"),
    (
        r"wc-admin/(launch-your-store|settings/payments|plugins|marketplace).*",
        "WooCommerce > Settings",
    ),
    (
        r"wc-admin/(mobile-app|blueprint|experiments|notice|tax|shipping|payment).*",
        "WooCommerce > Settings",
    ),
    (r"wc-admin/(marketing|features|options|themes).*", "WooCommerce > Marketing"),
    (r"wc-admin-email.*", "WooCommerce > Settings > Emails"),
    (r"tec/migrations/v1.*", "Events > Settings, the migration screen"),
    (r"tec/v2/onboarding.*", "Events > Settings, the setup wizard"),
    (r"tribe/event-aggregator/v1.*", "Events > Import"),
    (
        r"yoast/v1/(configuration|workouts|integrations|wincher|semrush|ai|introductions).*",
        "Yoast SEO > General",
    ),
)

_OUT: tuple[tuple[str, str], ...] = (
    (r"oembed/1\.0/proxy$", "fetches other sites' embeds for the block editor"),
    (r"wc/store(/v1)?(/.*)?$", "a shopper's cart and checkout, for visitors"),
    (r"wc/private(/.*)?$", "WooCommerce's own private calls"),
    (r"wc-telemetry(/.*)?$", "WooCommerce's usage reports to its makers"),
    (r"wc-push-notifications(/.*)?$", "notifications to WooCommerce's phone app"),
    (r"wccom-site/v3(/.*)?$", "the WooCommerce.com marketplace connection"),
    (r"wc/pos/v1.*", "WooCommerce's point-of-sale app"),
    (r"tribe/views/v2(/.*)?$", "calendar pages drawn for visitors"),
    (r"wp/v2/block-renderer.*", "previews drawn for the block editor"),
    (r"pmpro/v1/checkout_levels?$", "the checkout page's prices, for visitors"),
    (r"(baf|qaf)/v1/spam/pow$", "the proof-of-work puzzle a form page asks of visitors"),
    (
        r"mcp(/.*)?$",
        "the site's MCP server, for outside AI apps; Ask the Site reaches the same "
        "abilities through wp-abilities/v1, each run only after you say yes",
    ),
)

_PLANNED: tuple[tuple[str, str], ...] = (
    (r"wc/v[123](/.*)?$", "Sites > site > Shop"),
    (r"wc-analytics(/.*)?$", "Sites > site > Shop, reports"),
    (r"(tribe/events/v1|tec/v1)(/.*)?$", "Sites > site > Events Calendar"),
    (r"yoast/v1(/.*)?$", "Sites > site > SEO > Site SEO says which are wp-admin only"),
    (r"jetpack/v4(/.*)?$", "Sites > site > Jetpack"),
    (
        r"redirection/v1(/.*)?$",
        "Redirection's groups, import and options: More from This Site and the plugin's screen",
    ),
    (r"(baf|qaf)/v1(/.*)?$", "Sites > site > Forms, the builder"),
    (r"pmpro/v1(/.*)?$", "Sites > site > Memberships, where the site has no PMPro abilities"),
)

#: Form and membership plugins once considered and deferred (complete.md WP-C): QAF, Gravity
#: Forms and Paid Memberships Pro are the current commitments. These keep only the generic
#: doors every plugin gets, named here so none is quietly restored as if it were supported.
_DEFERRED: tuple[tuple[str, str], ...] = (
    (r"mp/v1(/.*)?$", "MemberPress"),
    (r"rcp/v1(/.*)?$", "Restrict Content Pro"),
    (r"wpforms/v1(/.*)?$", "WPForms"),
    (r"ninja-forms(-[a-z]+)?(/.*)?$", "Ninja Forms"),
    (r"frm/v2(/.*)?$", "Formidable Forms"),
    (r"contact-form-7/v1(/.*)?$", "Contact Form 7"),
    (r"fluentform/v1(/.*)?$", "Fluent Forms"),
    (r"forminator/v1(/.*)?$", "Forminator"),
    # Field plugins (field_plugins.FIELD_PLUGIN_SCOPE): the routes their adapters use are
    # covered (workbench_coverage_routes); the rest of their namespaces are only read.
    (r"pods/v1(/.*)?$", "Pods"),
    (r"cmb2/v1(/.*)?$", "CMB2"),
)

#: Jobs with no REST route at all, so no index lists them: each one's disposition.
NO_ROUTE: Mapping[str, RouteClass] = {
    "WordPress and translation updates": RouteClass(
        "wp_admin_only",
        "Dashboard > Updates (wp-admin/update-core.php); Needs My Attention > Updates",
    ),
    "plugin updates and automatic updates": RouteClass(
        "wp_admin_only", "Plugins (wp-admin/plugins.php); Open in Dashboard on a plugin row"
    ),
    "theme activate, install, update and automatic updates": RouteClass(
        "wp_admin_only", "Appearance > Themes (wp-admin/themes.php); Open in Dashboard"
    ),
    "Site Health Info tab": RouteClass(
        "wp_admin_only",
        "Tools > Site Health > Info (wp-admin/site-health.php?tab=debug); "
        "Sites > site > Site Health > Information",
    ),
    "XML-RPC (xmlrpc.php)": RouteClass(
        "out_of_scope",
        "deliberately unused: REST does every job, and XML-RPC takes a password per call; "
        "Sites > site > Site Health > Security warns when a site still answers on it",
    ),
}


@dataclass(frozen=True)
class SweepArea:
    """One row of the third sweep (PRD 15.11): what QUILL does, and where the rest is.

    *built* is the Workbench's own home for what core REST (or a verified
    route) reaches, empty when there is none; *plugins* names the plugins
    that provide the area; *namespaces* are their REST namespaces (each **to
    verify** against a live install); *screen* is the wp-admin page Open in
    Dashboard goes to when the site has none of them (a path under
    ``wp-admin/``), and *boundary* is the plain sentence of what QUILL will
    and will not do there.
    """

    area: str
    built: str
    plugins: str
    namespaces: tuple[str, ...]
    screen: str
    boundary: str


_GENERIC = (
    "QUILL has no adapter for these plugins: where the site lists one of their namespaces, "
    "its routes are read under More from This Site and written only through the REST "
    "Console's previews; otherwise Open in Dashboard."
)

#: Every third-sweep row this Workbench answers for, with its supported boundary.
#: Memberships, plugin directory and abandoned plugins, people, roles, moving in and
#: out, collaboration and Ask are recorded with their own nodes, not here.
THIRD_SWEEP: tuple[SweepArea, ...] = (
    SweepArea(
        "Redirects",
        "Sites > site > Redirects and its 404 Log, through redirection/v1",
        "Redirection; Yoast SEO Premium and Rank Math keep redirects in their own screens",
        ("redirection/v1",),
        "tools.php?page=redirection.php",
        "Redirection's redirects are listed, added, changed, turned on and off, deleted after "
        "a confirmation by name, and tested on the list as read; its 404 log is listed and an "
        "address in it can be redirected. Yoast and Rank Math redirects open their own screens.",
    ),
    SweepArea(
        "Privacy requests",
        "Sites > site > Privacy Requests, pointing to wp-admin",
        "WordPress itself",
        (),
        "export-personal-data.php",
        "Core has no REST route for export and erase requests, so QUILL opens wp-admin's "
        "Export and Erase Personal Data screens and never says a request was done.",
    ),
    SweepArea(
        "Content audit",
        "Sites > site > Content Audit",
        "WordPress itself",
        (),
        "edit.php?post_type=page",
        "Built from the posts and pages QUILL reads: orphans, stale, duplicate titles and "
        "text, length, reading level and heading order; Move to Trash shows who links first.",
    ),
    SweepArea(
        "Media housekeeping",
        "Sites > site > Media > Housekeeping",
        "WordPress itself",
        (),
        "upload.php",
        "Unused, uploaded-twice and very large files, video without captions and audio "
        "without a transcript; usage is shown before Move to Trash, which deletes nothing "
        "where the site keeps no media Trash.",
    ),
    SweepArea(
        "Search and sitemaps",
        "Sites > site > Search and Upkeep",
        "WordPress itself; Yoast SEO and Rank Math replace the sitemap",
        (),
        "options-reading.php",
        "Search engine visibility is judged from wp-sitemap.xml unless the site exposes "
        "blog_public; Settings > Reading says for certain.",
    ),
    SweepArea(
        "Scheduled tasks",
        "Sites > site > Search and Upkeep, Missed schedule rows",
        "WordPress itself; WP Crontrol lists every WP-Cron task",
        ("wp-crontrol/v1",),
        "site-health.php",
        "Posts and pages still Scheduled after their time are listed; no other WP-Cron task "
        "is visible to REST.",
    ),
    SweepArea(
        "SSL and the address",
        "Sites > site > Search and Upkeep, Certificate row",
        "WordPress itself",
        (),
        "site-health.php",
        "The expiry date comes from QUILL's own verified connection where Python hands it "
        "over; otherwise the row says only that the certificate is valid today.",
    ),
    SweepArea(
        "Someone else is editing",
        "Sites > site > Search and Upkeep, Editing locks; Properties' conflict check",
        "WordPress itself",
        (),
        "edit.php",
        "WordPress's _edit_lock is read where a site exposes it; otherwise items changed in "
        "the last 15 minutes are listed as maybe open, and a save never overwrites a newer "
        "change.",
    ),
    SweepArea(
        "Backups",
        "",
        "Jetpack Backup, UpdraftPlus, host tools",
        ("jetpack/v4",),
        "plugins.php?plugin_status=active",
        "Restores always open the plugin's own screen. " + _GENERIC,
    ),
    SweepArea(
        "Security, sign-ins and two-factor",
        "",
        "Wordfence, Solid Security, Shield Security, Patchstack, Two Factor",
        ("wordfence/v1", "ithemes-security/v1", "shield/v1", "two-factor/1.0"),
        "plugins.php?plugin_status=active",
        "Vulnerability data from a public database would need consent and an egress row, "
        "and is not fetched. " + _GENERIC,
    ),
    SweepArea(
        "Caching and speed",
        "",
        "WP Rocket, LiteSpeed Cache, W3 Total Cache, Jetpack Boost",
        ("litespeed/v1", "jetpack-boost/v1"),
        "plugins.php?plugin_status=active",
        "No cache is purged by QUILL. " + _GENERIC,
    ),
    SweepArea(
        "Multilingual sites",
        "",
        "Polylang, WPML, TranslatePress",
        ("pll/v1",),
        "plugins.php?plugin_status=active",
        "The editor's Mark Language marks passages. " + _GENERIC,
    ),
    SweepArea(
        "Consent and cookies",
        "",
        "Complianz, CookieYes and other consent plugins",
        ("complianz/v1",),
        "options-privacy.php",
        "Settings > Privacy names the privacy policy page; the banner's texts are checked "
        "with Check This Page. " + _GENERIC,
    ),
    SweepArea(
        "Email delivery",
        "",
        "WP Mail SMTP, FluentSMTP, Post SMTP",
        ("wp-mail-smtp/v1",),
        "plugins.php?plugin_status=active",
        "No test email is sent by QUILL. " + _GENERIC,
    ),
    SweepArea(
        "Newsletters and subscribers",
        "",
        "Jetpack Newsletter, MailPoet, The Newsletter Plugin",
        ("mailpoet/v1",),
        "plugins.php?plugin_status=active",
        "No newsletter is sent by QUILL. " + _GENERIC,
    ),
    SweepArea(
        "Courses",
        "",
        "LearnDash, LifterLMS, Tutor LMS, Sensei",
        ("ldlms/v2", "llms/v1", "tutor/v1", "sensei-internal/v1"),
        "plugins.php?plugin_status=active",
        "Course and lesson post types still appear under More Content Types when they are "
        "in REST. " + _GENERIC,
    ),
    SweepArea(
        "Event tickets and attendance",
        "",
        "Event Tickets, WooCommerce Bookings",
        ("tribe/tickets/v1",),
        "edit.php?post_type=tribe_events",
        "Events themselves are a discovered content type. " + _GENERIC,
    ),
    SweepArea(
        "Stats and analytics",
        "",
        "Jetpack Stats, Site Kit by Google, Independent Analytics",
        ("google-site-kit/v1", "jetpack/v4"),
        "index.php",
        "No visitor data is fetched from outside services. " + _GENERIC,
    ),
    SweepArea(
        "Social sharing",
        "",
        "Jetpack Social",
        ("jetpack/v4",),
        "plugins.php?plugin_status=active",
        "Nothing is shared to social accounts by QUILL. " + _GENERIC,
    ),
    SweepArea(
        "Shop, orders and catalogue",
        "Sites > site > Shop: products, orders, customers, coupons, reports, store settings",
        "WooCommerce and its extensions",
        ("wc/v3",),
        "admin.php?page=wc-admin",
        "Supported since 2026-11-13: products (filters, edit, new, duplicate, trash, "
        "variations), orders (status, notes, refunds typed to confirm, never batched), "
        "customers read, coupons, reports and store settings, each change previewed. "
        "Since 2026-11-14 also reviews, shipping zones, tax rates and classes, webhooks, "
        "attributes, brands, customers' details and variations. Subscriptions and bookings "
        "open wp-admin.",
    ),
    SweepArea(
        "SEO",
        "Sites > site > SEO and Site SEO (Yoast SEO)",
        "Yoast SEO, Rank Math",
        ("yoast/v1", "rankmath/v1"),
        "admin.php?page=wpseo_dashboard",
        "Yoast SEO is supported since 2026-11-13: per-post title, description, keyphrase and "
        "indexing through the meta it registers, search appearance, and site scores; what "
        "only Yoast's screens do is listed with Open in Dashboard. Rank Math: " + _GENERIC,
    ),
)


def sweep_disposition(area: SweepArea, namespaces: Iterable[str]) -> RouteClass:
    """Where *area* lives on a site whose index lists *namespaces*.

    Built rows are ``covered``; a plugin row whose namespace the site lists is
    ``schema_built`` (generic route browsing under More from This Site), and
    one whose namespace it does not list is ``wp_admin_only`` (Open in Dashboard).
    """
    listed = {n.strip("/") for n in namespaces}
    found = [n for n in area.namespaces if n in listed]
    if area.built and (found or not area.namespaces):
        return RouteClass("covered", area.built)
    if found:
        return RouteClass(
            "schema_built", f"More from This Site > {', '.join(found)}, read generically"
        )
    return RouteClass("wp_admin_only", f"Open in Dashboard: wp-admin/{area.screen}")


def _match(path: str, table: Iterable[tuple[str, str]]) -> str:
    for pattern, home in table:
        if re.match(pattern, path):
            return home
    return ""


def classify(route: str, methods: Iterable[str] = ()) -> RouteClass:
    """Where *route* (``/wp/v2/posts``) lives, by rule."""
    path = route.strip("/")
    for status, table in (
        ("out_of_scope", _OUT),
        ("covered", _COVERED),
        ("wp_admin_only", _WP_ADMIN),
        ("planned", _PLANNED),
    ):
        home = _match(path, table)
        if home:
            return RouteClass(status, home)
    readable = not methods or "GET" in set(methods)
    deferred = _match(path, _DEFERRED)
    if deferred:
        where = (
            "More from This Site lists it by namespace" if readable else "its own wp-admin screen"
        )
        return RouteClass(
            "schema_built" if readable else "wp_admin_only",
            f"{deferred}: deferred, not a current commitment; {where}",
        )
    if path.startswith("wp/v2/"):
        return RouteClass(
            "schema_built", "Sites > site > More Content Types or More Taxonomies, discovered"
        )
    if readable:
        return RouteClass("schema_built", "Sites > site > More from This Site, by namespace")
    return RouteClass("wp_admin_only", "the plugin's own screen in wp-admin")


def classify_index(routes: Mapping[str, object]) -> dict[str, RouteClass]:
    """Every route of a recorded index (route -> {"methods": [...]}) classified."""
    found: dict[str, RouteClass] = {}
    for route, info in routes.items():
        methods: list[str] = []
        if isinstance(info, Mapping):
            raw = info.get("methods")
            if isinstance(raw, list):
                methods = [str(m) for m in raw]
        found[route] = classify(route, methods)
    return found


def summary(classes: Mapping[str, RouteClass]) -> str:
    """ "412 covered, 120 built from their schema, ..." for the scorecard and Site Properties."""
    counts = Counter(c.status for c in classes.values())
    return (
        f"{counts['covered']} covered, {counts['schema_built']} built from their schema, "
        f"{counts['planned']} planned, {counts['wp_admin_only']} in wp-admin only, "
        f"{counts['out_of_scope']} out of scope"
    )


_WORDS = {
    "covered": "covered",
    "schema_built": "built from what the site says",
    "planned": "planned",
    "wp_admin_only": "in wp-admin only",
    "out_of_scope": "not for running a site",
}


def status_words(status: str) -> str:
    return _WORDS.get(status, status)


def coverage_table(classes: Mapping[str, RouteClass]) -> CoverageTable:
    """The routes as the shared engine's coverage table (built, planned, on the site only)."""
    engine = {
        "covered": CoverageStatus.BUILT,
        "schema_built": CoverageStatus.BUILT,
        "planned": CoverageStatus.PLANNED,
        "wp_admin_only": CoverageStatus.SITE_ONLY,
        "out_of_scope": CoverageStatus.SITE_ONLY,
    }
    return CoverageTable([
        CoverageRow(route, engine[c.status], c.home, feature=c.status)
        for route, c in sorted(classes.items())
    ])
