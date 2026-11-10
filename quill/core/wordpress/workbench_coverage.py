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

from quill.core.workbench.coverage import CoverageRow, CoverageStatus, CoverageTable

__all__ = [
    "STATUSES",
    "RouteClass",
    "classify",
    "classify_index",
    "coverage_table",
    "namespace_of",
    "status_words",
    "summary",
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


# (pattern on the path without its leading slash, home) for routes with a built home.
_COVERED: tuple[tuple[str, str], ...] = (
    (r"$", "the site's Overview, from its index"),
    (r"batch/v1$", "batch edits: Properties on several rows"),
    (r"wp/v2/(posts|pages)(/.*)?$", "Sites > site > Posts and Pages"),
    (r"wp/v2/media(/.*)?$", "Sites > site > Media"),
    (r"wp/v2/comments(/.*)?$", "Sites > site > Comments"),
    (r"wp/v2/(categories|tags)(/.*)?$", "Sites > site > Categories and Tags"),
    (r"wp/v2/users(/.*)?$", "Sites > site > People > Users and Application Passwords"),
    (r"wp/v2/plugins(/.*)?$", "Sites > site > Plugins"),
    (r"wp/v2/themes(/.*)?$", "Sites > site > Appearance > Themes"),
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
    (r"gf/v2/(forms|entries)(/.*)?$", "Sites > site > Forms"),
)

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
)

_PLANNED: tuple[tuple[str, str], ...] = (
    (r"wc/v[123](/.*)?$", "Sites > site > Shop"),
    (r"wc-analytics(/.*)?$", "Sites > site > Shop, reports"),
    (r"(tribe/events/v1|tec/v1)(/.*)?$", "Sites > site > Events, through its content type"),
    (r"yoast/v1(/.*)?$", "Sites > site > SEO"),
    (r"jetpack/v4(/.*)?$", "Sites > site > Jetpack"),
    (r"redirection/v1(/.*)?$", "Sites > site > Redirects (15.11)"),
    (r"(baf|qaf)/v1(/.*)?$", "Sites > site > Forms, the builder"),
)


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
