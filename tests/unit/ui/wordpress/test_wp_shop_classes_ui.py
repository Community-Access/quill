"""Shipping Classes and Generate Variations in the Workbench window (complete.md 2.3, Shop).

The real provider over a fake site answering in ``wc/v3``'s shapes; the dialogs answer
from queues and background work runs inline. No site is reached: live testing is deferred.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import workbench_shop_classes as classes  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS  # noqa: E402
from quill.core.wordpress.workbench_plugin_actions import KEYLESS, PLUGIN_NEW_HERE  # noqa: E402
from quill.core.wordpress.workbench_shop_catalog import product_row  # noqa: E402
from quill.core.workbench.properties import FieldKind  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import (  # noqa: E402
    SITE,
    _ref,
)
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import bench as _bench  # noqa: E402

bench = _bench

HEAVY = {"id": 31, "name": "Heavy items", "slug": "heavy-items", "description": "", "count": 4}
BULKY = {"id": 32, "name": "Bulky", "slug": "bulky", "description": "", "count": 0}
MUG = {
    "id": 9,
    "name": "Mug",
    "type": "variable",
    "status": "publish",
    "shipping_class": "heavy-items",
    "variations": [40],
    "attributes": [{"id": 1, "name": "Size", "variation": True, "options": ["S", "M", "L"]}],
}
PRODUCT_SCHEMA = {
    "sku": {"type": "string", "context": ["view", "edit"]},
    "shipping_class": {"type": "string", "description": "Shipping class slug.",
                       "context": ["view", "edit"]},
}  # fmt: skip


@pytest.fixture
def shop(bench, monkeypatch):
    plain = bench.api.get
    state: dict[str, Any] = {"mug": dict(MUG), "made": []}

    def get(route: str, **params: Any) -> Any:
        if route == classes.ROUTE:
            return [HEAVY, BULKY]
        if route == "wc/v3/products/9":
            return state["mug"]
        return plain(route, **params)

    def post(route: str, body: Any = None, **_p: Any) -> Any:
        bench.api.sent.append(("POST", route, body))
        if route.endswith("/variations/generate"):
            state["mug"] = {**MUG, "variations": [40, 41, 42]}
            return {"count": 2}
        if route == classes.ROUTE:
            return {"id": 33, **body}
        return {**HEAVY, **(body or {})}

    monkeypatch.setattr(bench.api, "get", get)
    monkeypatch.setattr(bench.api, "post", post)
    monkeypatch.setattr(
        bench.api,
        "request",
        lambda _m, _r, **_k: SimpleNamespace(payload={"schema": {"properties": PRODUCT_SCHEMA}}),
        raising=False,
    )
    return bench


def _class(raw: dict[str, Any] = HEAVY) -> Any:
    return classes.class_row(raw, SITE)


def _mug(kind: str = "variable") -> Any:
    return product_row({**MUG, "type": kind}, SITE)


# -- the tables -------------------------------------------------------------------------


def test_the_commands_are_on_their_rows_with_a_reason_for_no_key() -> None:
    labels = [r.label for r in WORDPRESS_ACTIONS.rows_for("shop_shipping_class")]
    assert labels[:4] == ["Read in Full", "Change...", "New Shipping Class...", "Delete..."]
    assert "Generate Variations..." in [r.label for r in WORDPRESS_ACTIONS.rows_for("shop_product")]
    assert PLUGIN_NEW_HERE["shop_shipping_classes"] == "do_new_shipping_class"
    for verb in ("change_shipping_class", "new_shipping_class", "delete_shipping_class",
                 "generate_variations"):  # fmt: skip
        assert KEYLESS[f"wordpress.workbench.{verb}"]


# -- shipping classes --------------------------------------------------------------------


def test_new_shipping_class_previews_makes_it_and_ctrl_z_deletes_it(shop) -> None:
    a = shop.answers
    a.texts += ["Fragile", "", "Wrap well"]
    shop.provider.do_new_here(_ref("shop_shipping_classes"), None)
    assert a.previews[-1]["summary"] == f"Make the shipping class Fragile on {SITE}."
    assert shop.api.sent[-1] == (
        "POST",
        "wc/v3/products/shipping_classes",
        {"name": "Fragile", "description": "Wrap well"},
    )
    assert shop.said[-1] == f"Made the shipping class Fragile on {SITE}."
    step = shop.provider.history.entries[-1]
    assert step.undo is not None
    step.undo()
    assert shop.api.sent[-1] == ("DELETE", "wc/v3/products/shipping_classes/33", None)


def test_a_bad_slug_is_said_and_nothing_is_made(shop) -> None:
    shop.answers.texts += ["Fragile", "not a slug", ""]
    shop.provider.do_new_shipping_class(_ref("shop_shipping_classes"), None)
    assert shop.api.sent == [] and shop.answers.previews == []
    assert shop.said[-1].endswith("Nothing was made.")


def test_change_sends_only_what_changed_after_a_preview_and_can_be_undone(shop) -> None:
    a = shop.answers
    a.texts += ["Heavy goods", "heavy-items", ""]
    shop.provider.do_change_shipping_class(_ref("shop_shipping_classes"), _class())
    assert a.previews[-1]["lines"][:2] == [
        f"The shipping class Heavy items on {SITE}:",
        "Name: Heavy items becomes Heavy goods.",
    ]
    assert shop.api.sent[-1] == (
        "POST",
        "wc/v3/products/shipping_classes/31",
        {"name": "Heavy goods"},
    )
    assert shop.said[-1].startswith(f"Changed the shipping class Heavy items on {SITE}.")
    assert shop.provider.history.entries[-1].undo is not None


def test_change_with_nothing_different_sends_nothing(shop) -> None:
    shop.answers.texts += ["Heavy items", "", ""]
    shop.provider.do_change_shipping_class(_ref("shop_shipping_classes"), _class())
    assert shop.api.sent == [] and shop.said[-1] == "Nothing about Heavy items would change."


def test_delete_names_the_class_and_the_site_and_is_for_good(shop) -> None:
    shop.provider.do_delete_shipping_class(_ref("shop_shipping_classes"), _class())
    preview = shop.answers.previews[-1]
    assert preview["summary"] == f"Delete the shipping class Heavy items on {SITE} for good?"
    assert "Its 4 products are left with no shipping class" in preview["lines"][1]
    assert preview["yes"] == "Delete"
    assert shop.api.sent[-1] == ("DELETE", "wc/v3/products/shipping_classes/31", None)
    assert shop.said[-1] == f"Deleted the shipping class Heavy items on {SITE}."
    assert shop.provider.history.entries[-1].undo is None


def test_a_declined_delete_sends_nothing(shop) -> None:
    shop.answers.yes = False
    shop.provider.do_delete_shipping_class(_ref("shop_shipping_classes"), _class())
    assert shop.api.sent == []


def test_a_products_properties_choose_its_shipping_class_by_name(shop) -> None:
    sheet, values, *_rest = shop.provider._load_sheet(_mug())
    spec = sheet.field("shipping_class")
    assert spec.kind is FieldKind.CHOICE
    assert spec.choice_words == ("No shipping class", "Bulky", "Heavy items")
    assert spec.word_for(values["shipping_class"]) == "Heavy items"


# -- Generate Variations ------------------------------------------------------------------


def test_generate_variations_previews_counts_and_undoes(shop) -> None:
    shop.provider.do_generate_variations(_ref("shop"), _mug())
    preview = shop.answers.previews[-1]
    assert preview["summary"] == f"Make every missing variation of Mug on {SITE}?"
    assert preview["lines"][0] == (
        f"Mug on {SITE} has 3 combinations of Size (3 values), and 1 variation now."
    )
    assert ("POST", "wc/v3/products/9/variations/generate", {}) in shop.api.sent
    assert shop.said[-1] == f"Made 2 variations of Mug on {SITE}."
    step = shop.provider.history.entries[-1]
    assert step.undo is not None
    assert step.undo() == f"Deleted 2 new variations of Mug on {SITE}."
    assert shop.api.sent[-2:] == [
        ("DELETE", "wc/v3/products/9/variations/41", None),
        ("DELETE", "wc/v3/products/9/variations/42", None),
    ]


def test_generate_variations_on_a_simple_product_says_why_and_sends_nothing(shop) -> None:
    shop.provider.do_generate_variations(_ref("shop"), _mug("simple"))
    assert shop.api.sent == [] and shop.answers.previews == []
    assert shop.said[-1] == (
        f"Mug on {SITE} is a simple product, not a variable one, so it has no variations to "
        "make. Nothing was sent."
    )


def test_a_declined_generate_sends_nothing(shop) -> None:
    shop.answers.yes = False
    shop.provider.do_generate_variations(_ref("shop"), _mug())
    assert shop.api.sent == []
