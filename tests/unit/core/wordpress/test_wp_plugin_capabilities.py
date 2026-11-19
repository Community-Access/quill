"""Review item 34: shop, event and membership writes name what they need."""

from __future__ import annotations

import pytest

from quill.core.wordpress.site import Account
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS
from quill.core.wordpress.workbench_permissions import PLUGIN_NEEDS, capability_for, refusal
from quill.core.workbench.actions import Tier


def _account(role: str, *caps: str) -> Account:
    return Account(1, "Jeff", "jeff", (role,), frozenset(caps))


def _need(kind: str, verb: str) -> str:
    row = next(r for r in WORDPRESS_ACTIONS.rows_for(kind) if r.command_id.endswith(f".{verb}"))
    return capability_for(row, kind)


@pytest.mark.parametrize(
    ("kind", "verb"),
    [
        ("shop_order", "refund_order"),
        ("shop_product", "edit_product"),
        ("tribe_event", "new_event"),
        ("user", "change_membership"),
    ],
)
def test_an_editor_is_told_before_the_plugin_refuses(kind: str, verb: str) -> None:
    editor = _account("editor", "edit_posts", "edit_others_posts", "publish_posts")
    said = refusal(_need(kind, verb), editor, "Radio")
    assert said and "You are an Editor on Radio." in said


def test_a_shop_manager_and_an_administrator_are_not_greyed() -> None:
    need = _need("shop_order", "refund_order")
    assert refusal(need, _account("shop_manager", "manage_woocommerce"), "Radio") == ""
    assert refusal(need, _account("administrator", "manage_options"), "Radio") == ""


def test_the_refusal_says_who_can() -> None:
    said = refusal(_need("shop_product", "edit_product"), _account("author", "edit_posts"), "Radio")
    assert said.startswith("Changing the shop needs the Shop Manager or Administrator role.")


def test_every_plugin_write_names_a_need() -> None:
    for kind in WORDPRESS_ACTIONS.row_types:
        if not kind.startswith(("shop", "tribe")):
            continue
        for row in WORDPRESS_ACTIONS.rows_for(kind):
            if row.tier is not Tier.READ:
                assert capability_for(row, kind), row.command_id
    assert set(PLUGIN_NEEDS) >= {"change_membership", "cancel_membership"}
