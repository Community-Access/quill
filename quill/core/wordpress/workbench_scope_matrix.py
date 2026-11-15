"""Every kind x scope x operation, classified: supported, or not and why (PRD 15.12).

The PRD asks that every kind, over every scope (one site, a Site Set, every
site, a network), with every operation the kind allows, be a row somebody
decided. :func:`matrix` is that table: each cell is a :class:`Support`, with
the Workbench command that does it when it is supported, and the reason --
in words a person reads in the window -- when it is not. A cell is never
blank; ``tests/unit/core/wordpress/test_wp_workbench_scope_matrix.py`` checks
that, checks the decided cells, and (with the window) that every handler named
here exists.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "ACROSS_MATRIX_KINDS",
    "ACROSS_OPS",
    "BY_NAME_KINDS",
    "BY_NAME_OPS",
    "SCOPES",
    "Support",
    "classify",
    "matrix",
    "by_name_support",
]

SCOPES = ("site", "site_set", "all_sites", "network")

BY_NAME_KINDS = (
    "terms",
    "fields",
    "authors",
    "media_usage",
    "patterns",
    "links",
    "blocks",
    "forms",
    "template_parts",
)
BY_NAME_OPS = ("find_uses", "rename", "split", "merge", "reassign", "replace")

ACROSS_MATRIX_KINDS = (
    "terms",
    "plugins",
    "themes",
    "users",
    "settings",
    "menus",
    "patterns",
    "starter_pages",
    "forms",
    "content_types",
    "role_pages",
    "redirects",
    "app_passwords",
    "spam_senders",
    "fleet",
)
ACROSS_OPS = (
    "variants",
    "make_same",
    "fill_missing",
    "merge",
    "remove",
    "update",
    "compare_styles",
    "promote_network",
)


@dataclass(frozen=True)
class Support:
    """One cell: whether it is supported, the command that does it, and the reason."""

    supported: bool
    reason: str
    handler: str = ""  # the provider's ``do_<verb>`` when supported


def _yes(handler: str, reason: str) -> Support:
    return Support(True, reason, handler)


def _no(reason: str) -> Support:
    return Support(False, reason)


_BY_NAME: Mapping[str, Mapping[str, Support]] = {
    "terms": {
        "find_uses": _yes("where_used", "Each post and page with the term."),
        "rename": _yes("rename_value", "The term's name and slug, one request."),
        "split": _yes("split_value", "Chosen items move to a new term."),
        "merge": _yes("merge_value", "Every item moves to another term; the old one is deleted."),
        "reassign": _yes("reassign_value", "Items move to another term; the old one stays."),
        "replace": _no("A term is renamed, merged or reassigned; Rename covers replacing it."),
    },
    "fields": {
        "find_uses": _yes("where_used", "Each item with the value; Find Missing finds the rest."),
        "rename": _yes("rename_value", "The value changes on every item that has it."),
        "split": _yes("split_value", "The value changes on chosen items only."),
        "merge": _yes("merge_value", "Every item takes another value already in use."),
        "reassign": _no("A field value belongs to no one, so there is nothing to reassign."),
        "replace": _no("Rename changes the value everywhere."),
    },
    "authors": {
        "find_uses": _yes("where_used", "Each item the person wrote, of every status."),
        "rename": _no("A person's name is changed on their own sheet, in People."),
        "split": _yes("split_value", "Chosen items go to another person."),
        "merge": _no(
            "WordPress joins two people only when one is deleted, with reassignment, in People."
        ),
        "reassign": _yes("reassign_value", "Every item goes to another person."),
        "replace": _no("Reassign gives the items to another person."),
    },
    "media_usage": {
        "find_uses": _yes(
            "where_used", "Each page showing it, and where it is the featured image."
        ),
        "rename": _no("A file's name is fixed when uploaded; its title is on its sheet."),
        "split": _no("A picture is one file; Replace swaps it everywhere it is used."),
        "merge": _no("Replace swaps one file for another everywhere it is used."),
        "reassign": _no("Media is attached to items, not to a person or term."),
        "replace": _yes("replace_value", "Another library file, everywhere it is used."),
    },
    "patterns": {
        "find_uses": _yes("where_used", "Each page that places the synced pattern."),
        "rename": _no("A pattern's title is on its own sheet, in Patterns."),
        "split": _no("A synced pattern is one record; Replace points pages at another."),
        "merge": _no("Replace points every page at another pattern."),
        "reassign": _no("Patterns are not owned by a term or person here."),
        "replace": _yes("replace_value", "Another synced pattern, on every page using this one."),
    },
    "links": {
        "find_uses": _yes("where_used", "Each page linking to the address."),
        "rename": _no("Replace changes the address on every page."),
        "split": _no("A link is an address; Replace changes it everywhere."),
        "merge": _no("Replace changes the address to another everywhere."),
        "reassign": _no("Links are not owned by a term or person."),
        "replace": _yes("replace_value", "Another address, on every page."),
    },
    "blocks": {
        "find_uses": _yes("where_used", "Each page with the block or shortcode."),
        "rename": _no("Replace renames a shortcode everywhere; a block's type is its markup."),
        "split": _no("A block or shortcode is a kind of content, not a value to split."),
        "merge": _no("Replace renames a shortcode to another everywhere."),
        "reassign": _no("Blocks are not owned by a term or person."),
        "replace": _yes(
            "replace_value",
            "Shortcodes only: another shortcode name everywhere. A block is not rewritten by "
            "name, because its type is its markup.",
        ),
    },
    "forms": {
        "find_uses": _yes("where_used", "Each page placing the form."),
        "rename": _no("A form's title is in the form's own window."),
        "split": _no("A form is one record; Replace points pages at another form."),
        "merge": _no("Replace points every page at another form; entries stay with each form."),
        "reassign": _no("Forms are not owned by a term or person."),
        "replace": _yes("replace_value", "Another form, by number, on every page placing it."),
    },
}

_TEMPLATE_PARTS: Mapping[str, Support] = {
    "find_uses": _yes("where_used", "Each template, post and page that places the part."),
    "rename": _yes(
        "rename_value",
        "The part's title, through wp/v2/template-parts; its slug stays, because templates "
        "place a part by slug.",
    ),
    "split": _no("A template part is one record; templates choose which part they place."),
    "merge": _no("Templates place a part by slug; which part they use is changed in the template."),
    "reassign": _no("Template parts are not owned by a term or person."),
    "replace": _no(
        "Templates place a part by slug; which part they use is changed in the template."
    ),
}

_ONE_SITE = "Across Sites compares two or more sites; on one site, use that site's own node."
_NO_NETWORK = (
    "WordPress's REST API has no network-wide form of this; each site of a network is "
    "changed as its own site."
)

_ACROSS: Mapping[str, Mapping[str, Support]] = {
    "terms": {
        "variants": _yes("read", "Slugs that differ, and the sites missing the term."),
        "make_same": _yes("make_same", "Name, slug and description; made where missing."),
        "fill_missing": _yes("make_same", "Make Them the Same makes it on the sites missing it."),
        "merge": _no("Merging moves a site's own posts; By Name > Merge does it on each site."),
        "remove": _no("Deleting a term everywhere is not offered: its posts differ on each site."),
        "update": _no("Terms have no versions to update."),
        "compare_styles": _no("Only themes have global styles."),
        "promote_network": _no("WordPress has no network-wide terms."),
    },
    "plugins": {
        "variants": _yes("read", "Versions and active or inactive, and the sites missing it."),
        "make_same": _yes("make_same", "Active or inactive, as the winner is."),
        "fill_missing": _yes(
            "install_missing",
            "Installed from WordPress.org by its slug, inactive, after a preview.",
        ),
        "merge": _no("Plugins are not merged."),
        "remove": _no(
            "Removing a plugin everywhere is not offered: some delete their data; remove it on "
            "each site."
        ),
        "update": _no("WordPress's REST API cannot run updates; Open in Dashboard opens Updates."),
        "compare_styles": _no("Only themes have global styles."),
        "promote_network": _no("Promote to Network is the network scope."),
    },
    "themes": {
        "variants": _yes("read", "Versions and which site has it active."),
        "make_same": _yes(
            "make_same",
            "WordPress's REST API cannot activate a theme, so each differing site's wp-admin "
            "Themes screen opens to activate it there.",
        ),
        "fill_missing": _yes(
            "install_missing",
            "WordPress's REST API cannot install a theme, so each missing site's Add New opens.",
        ),
        "merge": _no("Themes are not merged."),
        "remove": _no("WordPress's REST API cannot delete a theme."),
        "update": _no("WordPress's REST API cannot run updates; Open in Dashboard opens Updates."),
        "compare_styles": _yes("compare_styles", "Palette and font sizes in effect, site by site."),
        "promote_network": _no(
            "Network-enabling a theme has no REST route; use Network Admin > Themes."
        ),
    },
    "users": {
        "variants": _yes("read", "The person's role on each site, and the sites without them."),
        "make_same": _yes("make_same", "The winning role, on every site the person is on."),
        "fill_missing": _no(
            "Adding a person needs an email and a password chosen on that site: New Here, there."
        ),
        "merge": _no("WordPress joins people only by deleting one with reassignment, per site."),
        "remove": _no("Removing a person needs a reassignment chosen on each site, in People."),
        "update": _no("People have no versions to update."),
        "compare_styles": _no("Only themes have global styles."),
        "promote_network": _no("Making a super admin has no REST route; use Network Admin."),
    },
    "settings": {
        "variants": _yes("read", "Each value, and the sites with it."),
        "make_same": _yes("make_same", "The winning value, through each site's wp/v2/settings."),
        "fill_missing": _no("Every site's WordPress has its core settings; nothing is missing."),
        "merge": _no("Settings are not merged."),
        "remove": _no("A core setting cannot be removed."),
        "update": _no("Make Them the Same sets a value."),
        "compare_styles": _no("Only themes have global styles."),
        "promote_network": _no("Network settings have no REST route; use Network Admin."),
    },
    "menus": {
        "variants": _yes("read", "Each menu's items, and the sites without it."),
        "make_same": _yes(
            "make_same",
            "The winner's items, as links pointed at each site; item ids change, so it is final.",
        ),
        "fill_missing": _yes("make_same", "Make Them the Same makes the menu where it is missing."),
        "merge": _no("Two menus are not merged; Make Them the Same copies one."),
        "remove": _no("Deleting a menu everywhere is not offered."),
        "update": _no("Menus have no versions to update."),
        "compare_styles": _no("Only themes have global styles."),
        "promote_network": _no("WordPress has no network-wide menus."),
    },
    "patterns": {
        "variants": _yes("read", "Each synced pattern's content, and the sites without it."),
        "make_same": _yes("make_same", "The winner's content; made where it is missing."),
        "fill_missing": _yes("make_same", "Make Them the Same makes it on the sites missing it."),
        "merge": _no("Patterns are not merged."),
        "remove": _no("Deleting a pattern everywhere is not offered: pages place it."),
        "update": _no("Make Them the Same sets the content."),
        "compare_styles": _no("Only themes have global styles."),
        "promote_network": _no("WordPress has no network-wide patterns."),
    },
    "app_passwords": {
        "variants": _yes(
            "read",
            "Each password by name and person, on every site; others' only where you may edit "
            "that person (edit_users).",
        ),
        "make_same": _no("A password is made on each site and shown once; it cannot be copied."),
        "fill_missing": _no("A password is made on each site and shown once; it cannot be copied."),
        "merge": _no("Application passwords are not merged."),
        "remove": _yes(
            "revoke_everywhere",
            "Revoked on every site that has it, after a preview; a revoked password cannot be "
            "restored, so there is no undo.",
        ),
        "update": _no("A password has nothing to update; revoke it and make a new one."),
        "compare_styles": _no("Only themes have global styles."),
        "promote_network": _no("Application passwords are per site, even on a network."),
    },
}

_NOT_ACROSS: Mapping[str, str] = {
    "starter_pages": (
        "Starter page patterns come from each site's theme and plugins and are read-only over "
        "REST (wp/v2/block-patterns/patterns), so there is nothing to make the same."
    ),
    "forms": (
        "A form carries per-site entries and notification addresses that a copy would get "
        "wrong, so forms are not compared across sites."
    ),
    "content_types": (
        "Post types are registered by code or a plugin on each site; REST reads them and "
        "cannot make one."
    ),
    "role_pages": (
        "WordPress's REST API does not say which page is the privacy policy page; that is "
        "Settings > Privacy in wp-admin, on each site."
    ),
    "redirects": (
        "Core has no redirects API; the Redirection plugin's is per site and not yet checked "
        "against a live install (15.11)."
    ),
    "spam_senders": (
        "Core's comment blocklist (disallowed_keys) is not in wp/v2/settings, so it cannot be "
        "changed over REST."
    ),
}


def by_name_support(kind: str, op: str) -> Support:
    """One By Name cell on one site."""
    if kind == "template_parts":
        return _TEMPLATE_PARTS[op]
    return _BY_NAME[kind][op]


def classify(family: str, kind: str, scope: str, op: str) -> Support:
    """The cell for *family* (``by_name`` or ``across``), *kind*, *scope* and *op*."""
    if family == "by_name":
        if scope != "site":
            return _no(
                "By Name works inside one site, whose posts it reads; Across Sites compares "
                "names between sites."
            )
        return by_name_support(kind, op)
    if kind == "fleet":
        if op == "variants" and scope in ("site_set", "all_sites"):
            return _yes("read", "Every site in one list: health, backups, security and updates.")
        if scope == "site" and op == "variants":
            return _no("The site's own Site Health node reads one site.")
        return _no("The Fleet only reads; it changes nothing.")
    if kind in _NOT_ACROSS:
        return _no(_NOT_ACROSS[kind])
    if scope == "site":
        return _no(_ONE_SITE)
    if scope == "network":
        if kind == "plugins" and op == "promote_network":
            return _yes(
                "promote_network",
                "network-active through wp/v2/plugins, only where the site's plugin schema "
                "offers it (a multisite) and WordPress finds you a super admin.",
            )
        if op == "promote_network":
            return _ACROSS[kind][op]
        return _no(_NO_NETWORK)
    return _ACROSS[kind][op]


def matrix() -> dict[tuple[str, str, str, str], Support]:
    """Every cell: (family, kind, scope, op) -> :class:`Support`."""
    cells: dict[tuple[str, str, str, str], Support] = {}
    for kind in BY_NAME_KINDS:
        for scope in SCOPES:
            for op in BY_NAME_OPS:
                cells[("by_name", kind, scope, op)] = classify("by_name", kind, scope, op)
    for kind in ACROSS_MATRIX_KINDS:
        for scope in SCOPES:
            for op in ACROSS_OPS:
                cells[("across", kind, scope, op)] = classify("across", kind, scope, op)
    return cells
