"""Navigator nodes for Paid Memberships Pro data, and Site Health's two REST-less tabs.

Kept here, beside the membership nodes the tree already splices, so the tree
module stays inside its size budget (GATE-11).
"""

from __future__ import annotations

from typing import Any

from quill.core.workbench.tree import NodeSpec

__all__ = ["HEALTH_NODES", "MEMBERSHIP_NODES"]


def _node(key: str, label: str, parent: str | None = None, **kwargs: Any) -> NodeSpec:
    return NodeSpec(key, label, parent, **kwargs)


MEMBERSHIP_NODES = (
    _node("memberships", "Memberships", "site"),
    _node(
        "membership_levels",
        "Membership Levels",
        "memberships",
        loader="pmpro:levels",
        columns=("name", "signups", "initial", "billing", "expires"),
        row_type="pmpro",
    ),
    _node(
        "membership_orders",
        "Orders",
        "memberships",
        loader="pmpro:orders",
        columns=("code", "status", "total", "gateway", "date", "member", "level"),
        row_type="pmpro",
    ),
    _node(
        "membership_subscriptions",
        "Subscriptions",
        "memberships",
        loader="pmpro:subscriptions",
        columns=("subscription", "status", "next_payment", "billing", "gateway", "member"),
        row_type="pmpro",
    ),
    _node(
        "membership_renewals",
        "Renewals Due",
        "memberships",
        loader="pmpro:renewals",
        columns=("subscription", "status", "next_payment", "billing", "gateway", "member"),
        row_type="pmpro",
        home=False,
    ),
    _node(
        "membership_discount_codes",
        "Discount Codes",
        "memberships",
        loader="pmpro:discount_codes",
        columns=("code", "uses", "used", "starts", "expires", "levels"),
        row_type="pmpro",
    ),
)

HEALTH_NODES = (
    _node(
        "site_health_info",
        "Information",
        "site_health",
        loader="health:info",
        columns=("test", "status", "says"),
        row_type="problem",
    ),
    _node(
        "site_health_security",
        "Security",
        "site_health",
        loader="health:security",
        columns=("test", "status", "says"),
        row_type="problem",
    ),
)
