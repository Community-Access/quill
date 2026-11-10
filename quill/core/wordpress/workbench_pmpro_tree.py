"""Navigator nodes for Paid Memberships Pro data."""

from __future__ import annotations

from quill.core.workbench.tree import NodeSpec

__all__ = ["MEMBERSHIP_NODES"]


def _node(key: str, label: str, parent: str | None = None, **kwargs: object) -> NodeSpec:
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
)
