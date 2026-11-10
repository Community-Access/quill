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
from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.tree import NodeSpec, Scope

__all__ = ["ACROSS_NODES", "BY_NAME_NODES", "PLACES_ROWS", "SWEEP_NODES"]

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
        columns=("site", "state"),
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
        row_type="problem",
    ),
    _n(
        "privacy_requests",
        "Privacy Requests",
        "site",
        loader="sweep:privacy",
        columns=("problem", "status"),
        row_type="problem",
    ),
)

HOUSEKEEPING = _n(
    "media_housekeeping",
    "Housekeeping",
    "media",
    loader="sweep:housekeeping",
    columns=("problem", "status"),
    row_type="problem",
    home=False,
)


def _a(verb: str, label: str, **kwargs: Any) -> ActionRow:
    tier = kwargs.pop("tier", Tier.READ)
    needs = kwargs.pop("needs", "")
    help_text = kwargs.pop("help", "")
    default = kwargs.pop("default", False)
    return ActionRow(f"{_PREFIX}{verb}", label, tier, needs, help_text, default)


def places_rows(read: ActionRow, sheet: ActionRow) -> Mapping[str, tuple[ActionRow, ...]]:
    """The rows' menus, given the table's own Read in Full and Properties rows."""
    return {
        "value": (
            _a("where_used", "Where It Is Used", default=True, help="Each page that uses it."),
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
                "promote_network",
                "Promote to Network...",
                tier=Tier.WRITE,
                needs="activate_plugins",
                help="On a multisite network, activate the plugin for every site of it.",
            ),
            sheet,
        ),
        "fleet": (
            _a("open_site", "Open This Site", default=True, help="Select it in the tree."),
            sheet,
        ),
    }


PLACES_ROWS = places_rows
