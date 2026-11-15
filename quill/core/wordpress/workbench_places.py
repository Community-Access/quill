"""The Workbench's W8 and 15.11 places: their nodes and their rows' actions (PRD 15.11, 15.12).

Kept beside :mod:`quill.core.wordpress.workbench_tree` and
:mod:`quill.core.wordpress.workbench_actions`, which splice these in, so
each of those stays one readable table:

- :data:`ACROSS_NODES`: Across Sites (Ctrl+0) and its kinds, and the Fleet;
- :data:`BY_NAME_NODES`: each site's By Name branch, a node per kind;
- :data:`SWEEP_NODES`: Content Audit and Privacy Requests;
- :data:`PLACES_ROWS`: what the rows of those places offer.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.workbench_across import ACROSS_KINDS, SITE_KINDS
from quill.core.wordpress.workbench_gap_actions import CHECK_LINKS
from quill.core.wordpress.workbench_sweep_places import SWEEP_MORE_NODES
from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.tree import NodeSpec, Scope

__all__ = ["ACROSS_NODES", "BY_NAME_NODES", "KEYLESS", "PLACES_ROWS", "SWEEP_NODES"]

_PREFIX = "wordpress.workbench."


def _n(key: str, label: str, parent: str | None = None, **kwargs: Any) -> NodeSpec:
    return NodeSpec(key, label, parent, **kwargs)


ACROSS_NODES: tuple[NodeSpec, ...] = (
    _n("across", "Across Sites", scope=Scope.ACCOUNT),
    *(
        _n(
            f"across_{kind}",
            label,
            "across",
            loader=f"across:{kind}",
            columns=("name", "sites", "versions", "missing"),
            row_type="across",
        )
        for kind, label in ACROSS_KINDS.items()
    ),
    _n(
        "fleet",
        "Fleet",
        "across",
        loader="across:fleet",
        columns=("site", "state", "health", "backups", "security", "updates"),
        row_type="fleet",
    ),
)

BY_NAME_NODES: tuple[NodeSpec, ...] = (
    _n("by_name", "By Name", "site"),
    *(
        _n(
            f"by_name_{kind}",
            label,
            "by_name",
            loader=f"scan:{kind}",
            columns=("value", "used"),
            row_type="value",
        )
        for kind, label in SITE_KINDS.items()
    ),
)

SWEEP_NODES: tuple[NodeSpec, ...] = (
    _n(
        "content_audit",
        "Content Audit",
        "site",
        loader="sweep:audit",
        columns=("problem", "status"),
        row_type="finding",
    ),
    _n(
        "privacy_requests",
        "Privacy Requests",
        "site",
        loader="sweep:privacy",
        columns=("problem", "status"),
        row_type="privacy",
    ),
    *SWEEP_MORE_NODES,
)

HOUSEKEEPING = _n(
    "media_housekeeping",
    "Housekeeping",
    "media",
    loader="sweep:housekeeping",
    columns=("problem", "status"),
    row_type="finding",
    home=False,
)


def _a(verb: str, label: str, **kwargs: Any) -> ActionRow:
    tier = kwargs.pop("tier", Tier.READ)
    needs = kwargs.pop("needs", "")
    help_text = kwargs.pop("help", "")
    default = kwargs.pop("default", False)
    return ActionRow(f"{_PREFIX}{verb}", label, tier, needs, help_text, default)


PLUGIN_BLOCK_USES = _a(
    "plugin_block_uses",
    "Pages Using Its Blocks",
    help="Before a plugin is removed: every page using a block from its namespace.",
)
"""On a block row of By Name and on a plugin's row (PRD 15.12)."""


def places_rows(read: ActionRow, sheet: ActionRow) -> Mapping[str, tuple[ActionRow, ...]]:
    """The rows' menus, given the table's own Read in Full and Properties rows."""
    return {
        "value": (
            _a("where_used", "Where It Is Used", default=True, help="Each page that uses it."),
            _a(
                "rename_value",
                "Rename Everywhere...",
                tier=Tier.WRITE,
                help="A new name or value wherever it is used, previewed item by item first.",
            ),
            _a(
                "split_value",
                "Split...",
                tier=Tier.WRITE,
                help="Chosen items move to a new term, value or person; the rest stay.",
            ),
            _a(
                "merge_value",
                "Merge Into...",
                tier=Tier.WRITE,
                help="Every item moves to another term or value; a merged term is deleted.",
            ),
            _a(
                "reassign_value",
                "Reassign...",
                tier=Tier.WRITE,
                help="Every item moves to another term or person; this one stays.",
            ),
            _a(
                "replace_value",
                "Replace Everywhere...",
                tier=Tier.WRITE,
                help="Another file, pattern, link, shortcode or form in every page using this.",
            ),
            _a(
                "find_missing",
                "Find Items Missing This Field",
                help="The posts and pages with no value for this custom field.",
            ),
            _a(
                "convert_shortcode",
                "Convert to Block...",
                tier=Tier.WRITE,
                help="A core shortcode, such as gallery or caption, made its core block on the "
                "items you check, previewed item by item first.",
            ),
            _a(
                "update_pattern",
                "Update Pattern Everywhere...",
                tier=Tier.WRITE,
                help="Change a synced pattern's content once; every page placing it shows it.",
            ),
            _a(
                "detach_pattern",
                "Detach Copies...",
                tier=Tier.WRITE,
                help="The pages you check get the pattern's own blocks, no longer synced.",
            ),
            PLUGIN_BLOCK_USES,
            CHECK_LINKS,
            sheet,
        ),
        "across": (
            read,
            _a(
                "make_same",
                "Make Them the Same...",
                tier=Tier.WRITE,
                help="Choose the version that wins; every site's change is previewed first.",
            ),
            _a(
                "merge_everywhere",
                "Merge Everywhere...",
                tier=Tier.WRITE,
                help="A tag or category: on each site, every post moves to another term you "
                "name, and this one is deleted, previewed site by site.",
            ),
            _a(
                "remove_everywhere",
                "Remove Everywhere...",
                tier=Tier.DESTRUCTIVE,
                help="A term, redirect or blocked sender, deleted on every site that has it, "
                "after a preview.",
            ),
            _a(
                "promote_network",
                "Promote to Network...",
                tier=Tier.WRITE,
                needs="activate_plugins",
                help="On a multisite network, activate the plugin for every site of it.",
            ),
            _a(
                "revoke_everywhere",
                "Revoke Everywhere...",
                tier=Tier.WRITE,
                help="An application password, revoked on every site that has it, after a "
                "preview. It cannot be undone.",
            ),
            _a(
                "compare_styles",
                "Compare Global Styles",
                help="Each site's palette and font sizes in effect, and which differ.",
            ),
            sheet,
        ),
        "fleet": (
            _a("open_site", "Open This Site", default=True, help="Select it in the tree."),
            sheet,
        ),
    }


PLACES_ROWS = places_rows

KEYLESS: dict[str, str] = {
    f"{_PREFIX}where_used": "The rows' Enter, so it needs no chord of its own.",
    f"{_PREFIX}rename_value": "Renaming everywhere is occasional and previewed (rule 9).",
    f"{_PREFIX}split_value": "Splitting a term or value is occasional and previewed (rule 9).",
    f"{_PREFIX}merge_value": "Merging is occasional and previewed (rule 9).",
    f"{_PREFIX}reassign_value": "Reassigning is occasional and previewed (rule 9).",
    f"{_PREFIX}replace_value": "Replacing everywhere is occasional and previewed (rule 9).",
    f"{_PREFIX}find_missing": "A check made now and then, on field rows only (rule 9).",
    f"{_PREFIX}make_same": "Aligning sites is occasional and previewed site by site (rule 9).",
    f"{_PREFIX}promote_network": "Done once per plugin on a network, rarely (rule 9).",
    f"{_PREFIX}compare_styles": "Comparing styles across sites is occasional (rule 9).",
    f"{_PREFIX}revoke_everywhere": "Revoking a leaked password everywhere is rare (rule 9).",
    f"{_PREFIX}convert_shortcode": "Converting shortcodes is done once per site (rule 9).",
    f"{_PREFIX}update_pattern": "Changing a pattern for every page is occasional (rule 9).",
    f"{_PREFIX}detach_pattern": "Detaching copies is occasional and previewed (rule 9).",
    f"{_PREFIX}plugin_block_uses": "A check before removing a plugin, now and then (rule 9).",
    f"{_PREFIX}merge_everywhere": "Merging terms on every site is rare and previewed (rule 9).",
    f"{_PREFIX}remove_everywhere": "Removing on every site is rare and previewed (rule 9).",
}
"""Why each By Name and Across Sites row command has no chord (family rule 8)."""
