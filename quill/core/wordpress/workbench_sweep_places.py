"""The site administration sweep's nodes, row menus and keyless reasons (PRD 15.11; WP-G).

Spliced into :mod:`quill.core.wordpress.workbench_places` (the nodes) and
:mod:`quill.core.wordpress.workbench_actions` (the row menus), so each of
those stays one table:

- :data:`SWEEP_MORE_NODES`: Redirects and its 404 Log, Search and Upkeep,
  and Administration Areas (every third-sweep row with this site's
  disposition, from :data:`quill.core.wordpress.workbench_coverage.THIRD_SWEEP`);
- :func:`sweep_rows`: the menus of findings, redirects, 404s, privacy
  pointers, upkeep rows and areas;
- :data:`KEYLESS`: why each of those commands has no chord (family rule 8).
  Add Redirect is reached by Ctrl+N (New Here) on Redirects.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.tree import NodeSpec

__all__ = ["KEYLESS", "SWEEP_MORE_NODES", "SWEEP_NODE_HELP", "SWEEP_ROW_HELP", "sweep_rows"]

_PREFIX = "wordpress.workbench."


def _n(key: str, label: str, parent: str, **kwargs: Any) -> NodeSpec:
    return NodeSpec(key, label, parent, **kwargs)


SWEEP_MORE_NODES: tuple[NodeSpec, ...] = (
    _n(
        "redirects",
        "Redirects",
        "site",
        loader="sweep:redirects",
        columns=("source", "target", "code", "hits", "state"),
        row_type="redirect",
    ),
    _n(
        "not_found_log",
        "404 Log",
        "redirects",
        loader="sweep:not_found",
        columns=("address", "when", "from"),
        row_type="not_found",
    ),
    _n(
        "site_upkeep",
        "Search and Upkeep",
        "site",
        loader="sweep:upkeep",
        columns=("what", "state", "source"),
        row_type="upkeep",
    ),
    _n(
        "admin_areas",
        "Administration Areas",
        "site",
        loader="sweep:areas",
        columns=("area", "where", "plugins"),
        row_type="sweep_area",
    ),
)

SWEEP_NODE_HELP: Mapping[str, str] = {
    "redirects": "The Redirection plugin's redirects: add with Ctrl+N, change, test, turn off.",
    "not_found_log": "Addresses visitors asked for that were not found; redirect any of them.",
    "site_upkeep": "Search visibility, the sitemap, missed schedules, the certificate and who "
    "is editing, each with where QUILL's answer comes from.",
    "admin_areas": "Every part of running a site: what QUILL does, and where the rest is.",
}

SWEEP_ROW_HELP: Mapping[str, str] = {
    "finding": "Something the audit found. Enter reads it; Show Where It Is Used comes "
    "before Move to Trash.",
    "redirect": "One redirect: from, to, its code and hits. Test an Address follows it.",
    "not_found": "An address that was not found. Redirect This Address sends it somewhere.",
    "privacy": "A wp-admin screen for privacy requests. Enter opens it in your browser.",
    "upkeep": "One upkeep check, ending with where its answer comes from.",
    "sweep_area": "One part of running a site. Enter goes where QUILL or wp-admin handles it.",
}


def _a(verb: str, label: str, help: str, **kwargs: Any) -> ActionRow:  # noqa: A002 - field
    return ActionRow(
        f"{_PREFIX}{verb}",
        label,
        kwargs.get("tier", Tier.READ),
        kwargs.get("needs", ""),
        help,
        kwargs.get("default", False),
    )


_SHOW_USAGE = _a("show_usage", "Show Where It Is Used", "Every page that uses or links to it.")
_TEST = _a(
    "test_address",
    "Test an Address...",
    "Follow the redirects read from this site from an address you give, naming chains "
    "and loops. Nothing is sent.",
)
_ADD = _a(
    "add_redirect",
    "Add Redirect...",
    "A new redirect from an old address to a new one, after a preview. Ctrl+N on Redirects.",
    tier=Tier.WRITE,
    needs="manage_options",
)


def sweep_rows(read: ActionRow, sheet: ActionRow) -> Mapping[str, tuple[ActionRow, ...]]:
    """The sweep rows' menus, given the table's own Read in Full and Properties rows."""
    open_site = _a("open_on_site", "Open on the Site", "In your browser. Shift+Enter.")
    read_too = _a("read", "Read in Full", "Move to the details pane to read it.")
    return {
        "finding": (
            read,
            _SHOW_USAGE,
            _a(
                "trash_finding",
                "Move to Trash...",
                "Its usage first, then into WordPress's Trash. Media is never deleted for good "
                "from here.",
                tier=Tier.ORGANIZE,
                needs="delete_posts",
            ),
            open_site,
            sheet,
        ),
        "redirect": (
            read,
            _TEST,
            _ADD,
            _a(
                "edit_redirect",
                "Change Redirect...",
                "Change where it leads from or to, or its code, after a preview.",
                tier=Tier.WRITE,
                needs="manage_options",
            ),
            _a(
                "toggle_redirect",
                "Turn On or Off",
                "Stop it redirecting without deleting it, or start it again.",
                tier=Tier.WRITE,
                needs="manage_options",
            ),
            _a(
                "delete_redirect",
                "Delete Redirect...",
                "Gone for good, after you confirm by name: the plugin keeps no Trash.",
                tier=Tier.DESTRUCTIVE,
                needs="manage_options",
            ),
            open_site,
            sheet,
        ),
        "not_found": (
            read,
            _a(
                "redirect_not_found",
                "Redirect This Address...",
                "A redirect from this address to one you give, after a preview.",
                tier=Tier.WRITE,
                needs="manage_options",
            ),
            _TEST,
            sheet,
        ),
        "privacy": (
            _a(
                "open_privacy",
                "Open This wp-admin Screen",
                "In your browser, where requests are confirmed and done. Enter.",
                default=True,
            ),
            read_too,
            sheet,
        ),
        "upkeep": (
            read,
            _a(
                "open_on_site",
                "Open Where It Is Checked",
                "The page or wp-admin screen this answer is about, in your browser.",
            ),
            sheet,
        ),
        "sweep_area": (
            _a(
                "open_area",
                "Go There",
                "QUILL's node for it, the plugin's routes, or its wp-admin screen. Enter.",
                default=True,
            ),
            read_too,
            sheet,
        ),
    }


KEYLESS: dict[str, str] = {
    f"{_PREFIX}show_usage": "Read before tidying up, a few times a year (rule 9).",
    f"{_PREFIX}trash_finding": "Tidying after an audit is occasional, and previewed (rule 9).",
    f"{_PREFIX}test_address": "Asked when a link is reported broken, now and then (rule 9).",
    f"{_PREFIX}add_redirect": "Ctrl+N (New Here) on Redirects reaches it; no chord of its own.",
    f"{_PREFIX}edit_redirect": "Redirects change rarely (rule 9).",
    f"{_PREFIX}toggle_redirect": "Redirects are turned off rarely (rule 9).",
    f"{_PREFIX}delete_redirect": "A destructive, rare job: never a bare key (rule 4).",
    f"{_PREFIX}redirect_not_found": "Reviewing the 404 log is a monthly job (rule 9).",
    f"{_PREFIX}open_privacy": "Enter opens it; privacy requests are rare (rule 9).",
    f"{_PREFIX}open_area": "Enter does it on the row.",
}
"""Why each command here has no chord (family rule 8)."""
