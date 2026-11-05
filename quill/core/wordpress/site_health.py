"""Site Check, every test, and the plugins QUILL recognises (wordpress.md 9.15).

Two things Site Check says that it could not say before:

* **Every Site Health test the site offers**, one line each. The tests are
  read from the site's own REST index (each is a route under
  ``wp-site-health/v1/tests/``), so a newer WordPress with a new test is
  covered without a change here. An index without routes falls back to the
  five tests every WordPress since 5.6 has.
* **Which plugins QUILL recognises** (:data:`RECOGNISED`), and what each one
  turns on in QUILL. Without the plugin nothing shows.

When the authorization-header test fails, one more line says what that
means for QUILL: application passwords cannot work, and why.

Wx-free; every request goes through
:class:`~quill.core.wordpress.api.WordPressApi`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import rendered
from quill.core.wordpress.site_admin import CheckLine

#: The tests every WordPress since 5.6 offers, for an index that lists no routes.
FALLBACK_TESTS: tuple[str, ...] = (
    "background-updates",
    "loopback-requests",
    "https-status",
    "dotorg-communication",
    "authorization-header",
)

#: What each test is about, for a site that answers without a label.
TEST_NAMES: dict[str, str] = {
    "background-updates": "Background updates",
    "loopback-requests": "Loopback requests",
    "https-status": "HTTPS",
    "dotorg-communication": "Reaching WordPress.org",
    "authorization-header": "The authorization header",
    "page-cache": "Page cache",
}

_TEST_ROUTE = re.compile(r"^/wp-site-health/v1/tests/([a-z0-9-]+)$")
_STATUSES = ("critical", "recommended", "good", "info")

AUTHORIZATION_EXPLAINED = (
    "What this means for QUILL: the web server drops the Authorization header "
    "before WordPress sees it, so application passwords cannot work. Every "
    "request QUILL signs arrives looking signed out, and the site refuses it. "
    "The host or the site's administrator can fix it, usually with one line in "
    "the site's .htaccess file; WordPress's own Site Health screen links to how."
)


def health_test_names(index: Mapping[str, Any]) -> list[str]:
    """Every Site Health test the index lists, in its order; the five known ones
    when the index lists no routes at all."""
    routes = index.get("routes")
    if not isinstance(routes, Mapping) or not routes:
        return list(FALLBACK_TESTS)
    found = [m.group(1) for r in routes if (m := _TEST_ROUTE.match(str(r)))]
    return list(dict.fromkeys(found))


def health_lines(api: WordPressApi, index: Mapping[str, Any]) -> list[CheckLine]:
    """One line per Site Health test, or one line saying the site offers none."""
    namespaces = [str(n) for n in index.get("namespaces", []) or []]
    if "wp-site-health/v1" not in namespaces:
        return [
            CheckLine(
                "info",
                "PHP version, updates and loopback: this site does not offer its "
                "health checks to QUILL.",
            )
        ]
    out: list[CheckLine] = []
    for test in health_test_names(index):
        try:
            raw = api.get(f"wp-site-health/v1/tests/{test}")
        except WordPressApiError as exc:
            if exc.status in (401, 403):
                return [CheckLine("info", "Health checks: only an administrator can run them.")]
            out.append(
                CheckLine(
                    "info",
                    f"{TEST_NAMES.get(test, _words(test))}: the site could not run this test.",
                )
            )
            continue
        if not isinstance(raw, dict):
            continue
        out.extend(health_test_lines(test, raw))
    return out


def health_test_lines(test: str, raw: Mapping[str, Any]) -> list[CheckLine]:
    """One test's answer as a line, plus the explanation when the header is lost."""
    status = str(raw.get("status", "info"))
    status = status if status in _STATUSES else "info"
    label = rendered(raw.get("label")) or TEST_NAMES.get(test, _words(test))
    lines = [CheckLine(status, f"{label.rstrip('.')}.")]
    if test == "authorization-header" and status != "good":
        lines.append(CheckLine(status, AUTHORIZATION_EXPLAINED))
    return lines


def _words(test: str) -> str:
    return test.replace("-", " ").capitalize()


# --------------------------------------------------------------------------- #
# Plugins QUILL recognises

#: namespace -> (plugin, what QUILL turns on for it). QUILL Accessible Forms is
#: section 17a's, and recognised there.
RECOGNISED: tuple[tuple[str, str, str], ...] = (
    (
        "tribe/events/v1",
        "The Events Calendar",
        "events with their start, end and venue in Properties, New Event, and Coming Up",
    ),
    (
        "wc/v3",
        "WooCommerce",
        "products with their price and stock in Properties, and Shop Orders to read",
    ),
    ("yoast/v1", "Yoast SEO", "the SEO title and description in Properties"),
    ("rankmath/v1", "Rank Math", "the SEO title and description in Properties"),
    (
        "wp-abilities/v1",
        "Abilities for AI",
        "Ask the Site, with each ability off until you turn it on",
    ),
)


def recognised(index: Mapping[str, Any]) -> list[tuple[str, str]]:
    """``(plugin, what QUILL turns on)`` for each recognised namespace the site has."""
    namespaces = {str(n) for n in index.get("namespaces", []) or []}
    return [(name, what) for ns, name, what in RECOGNISED if ns in namespaces]


def recognised_lines(index: Mapping[str, Any]) -> list[CheckLine]:
    return [
        CheckLine("info", f"{name}: recognised. QUILL offers {what}.")
        for name, what in recognised(index)
    ]
