"""complete.md 2.3 (Shop): shipping classes and Generate Variations, wx-free, over recorded answers.

The answers are in the shapes WooCommerce's ``wc/v3`` gives (``products/shipping_classes``
and ``products/{id}/variations/generate``, which answers ``{"count": n}``). No site is
reached: live testing is deferred.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.wordpress import workbench_shop_classes as classes
from quill.core.wordpress import workbench_shop_variations as variations
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import ShopValueError
from quill.core.wordpress.workbench_plugin_nodes import PLUGIN_NODE_HELP, PLUGIN_ROW_HELP
from quill.core.wordpress.workbench_shop import SHOP_NODES, load_shop
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec

SITE = "Radio"
HEAVY = {
    "id": 31,
    "name": "Heavy items",
    "slug": "heavy-items",
    "description": "Over 20 kg",
    "count": 4,
}
BULKY = {"id": 32, "name": "Bulky", "slug": "bulky", "description": "", "count": 1}
MUG = {
    "id": 9,
    "name": "Mug",
    "type": "variable",
    "variations": [40, 41],
    "attributes": [
        {"id": 1, "name": "Size", "variation": True, "options": ["Small", "Large"]},
        {"id": 2, "name": "Colour", "variation": True, "options": ["Red", "Blue", "Green"]},
        {"id": 3, "name": "Material", "variation": False, "options": ["Clay"]},
    ],
}


class Api:
    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []

    def get(self, route: str, **_p: Any) -> Any:
        found = self.answers.get(route, [])
        if isinstance(found, Exception):
            raise found
        return found

    def iter_collection(self, route: str, *_a: Any, **_k: Any):
        found = self.get(route)
        yield from found if isinstance(found, list) else []

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.sent.append(("POST", route, body))
        return self.answers.get(f"POST {route}", {})


def _ctx(api: Api, *namespaces: str) -> Any:
    info = SimpleNamespace(namespaces=namespaces or ("wc/v3",), routes=())
    return SimpleNamespace(api=api, name=SITE, info=info, url="https://radio.example")


# -- shipping classes -------------------------------------------------------------------


def test_shipping_classes_is_a_node_under_shop_with_its_help() -> None:
    node = next(n for n in SHOP_NODES if n.key == "shop_shipping_classes")
    assert (node.label, node.parent, node.loader) == (
        "Shipping Classes",
        "shop",
        "shop:shipping_classes",
    )
    assert node.row_type == "shop_shipping_class"
    assert PLUGIN_NODE_HELP["shop_shipping_classes"]
    assert PLUGIN_ROW_HELP["shop_shipping_class"]


def test_classes_load_by_name_with_their_slug_and_product_count() -> None:
    api = Api({classes.ROUTE: [HEAVY, BULKY]})
    rows = load_shop(_ctx(api), "shop", "shipping_classes", {})
    assert [r.title for r in rows] == ["Bulky", "Heavy items"]
    heavy = rows[1]
    assert heavy.kind == "shop_shipping_class" and heavy.key == "31"
    assert heavy.cells == {"name": "Heavy items", "slug": "heavy-items", "products": "4"}
    assert heavy.detail == "The shipping class Heavy items (heavy-items), on 4 products. Over 20 kg"


def test_a_site_without_a_shop_is_told_so() -> None:
    with pytest.raises(WordPressApiError, match="no shop QUILL can read"):
        load_shop(_ctx(Api({}), "wp/v2"), "shop", "shipping_classes", {})


def test_a_new_class_sends_what_was_given_and_its_preview_names_the_site() -> None:
    body = classes.class_body({}, {"name": " Heavy  items ", "slug": "", "description": ""})
    assert body == {"name": "Heavy items"}
    assert classes.class_preview(SITE, {}, body) == [
        "A new shipping class on Radio: Heavy items, with a slug made from its name.",
        "A product is put in it from its Properties. Ctrl+Z deletes it again.",
    ]
    full = classes.class_body({}, {"name": "Bulky", "slug": "Bulky-Box", "description": "Big"})
    assert full == {"name": "Bulky", "slug": "bulky-box", "description": "Big"}


def test_a_change_sends_only_what_changed_and_a_blank_slug_keeps_the_old_one() -> None:
    row = classes.class_row(HEAVY, SITE)
    old = row.raw["_loaded"]
    answers = {"name": "Heavy items", "slug": "", "description": "Over 25 kg"}
    body = classes.class_body(old, answers)
    assert body == {"description": "Over 25 kg"}
    assert classes.class_preview(SITE, old, body) == [
        "The shipping class Heavy items on Radio:",
        "Description: Over 20 kg becomes Over 25 kg.",
        "Its products stay in it, and shipping zones' rates for it still apply.",
    ]
    same = {"name": "Heavy items", "slug": "heavy-items", "description": "Over 20 kg"}
    assert classes.class_body(old, same) == {}


@pytest.mark.parametrize(
    ("answers", "says"),
    [
        ({"name": "  ", "slug": "", "description": ""}, "needs a name"),
        ({"name": "Heavy", "slug": "heavy items", "description": ""}, "is not a slug"),
        ({"name": "Heavy", "slug": "heavy--items", "description": ""}, "is not a slug"),
    ],
)
def test_a_class_is_checked_before_anything_is_sent(answers: dict[str, str], says: str) -> None:
    with pytest.raises(ShopValueError, match=says):
        classes.class_body({}, answers)


def test_the_delete_preview_names_the_class_and_what_its_products_lose() -> None:
    lines = classes.delete_lines(classes.class_row(HEAVY, SITE))
    assert lines[0].startswith("The shipping class Heavy items (heavy-items)")
    assert lines[1] == (
        "There is no Trash. Its 4 products are left with no shipping class, and any rate a "
        "shipping zone sets for it stops applying."
    )
    one = classes.delete_lines(classes.class_row(BULKY, SITE))[1]
    assert "Its 1 product is left with no shipping class" in one
    empty = classes.delete_lines(classes.class_row({**BULKY, "count": 0}, SITE))[1]
    assert "No product is in it" in empty


def _product_sheet() -> SheetSpec:
    fields = (
        FieldSpec("sku", "SKU"),
        FieldSpec("shipping_class", "Shipping class", help="Shipping class slug."),
    )
    return SheetSpec("shop_product", "Shop Product", (PageSpec("general", "General", fields),))


def test_properties_offer_the_shipping_class_by_name() -> None:
    values: dict[str, Any] = {"shipping_class": "heavy-items"}
    sheet = classes.with_class_choice(_product_sheet(), values, [HEAVY, BULKY])
    spec = sheet.field("shipping_class")
    assert spec.kind is FieldKind.CHOICE
    assert spec.choices == ("", "bulky", "heavy-items")
    assert spec.choice_words == ("No shipping class", "Bulky", "Heavy items")
    assert spec.word_for(values["shipping_class"]) == "Heavy items"
    assert spec.value_for("Bulky") == "bulky"  # what a save sends
    assert spec.value_for("No shipping class") == ""
    assert sheet.field("sku").kind is FieldKind.TEXT


def test_a_class_the_shop_no_longer_has_stays_offered_as_itself() -> None:
    values: dict[str, Any] = {"shipping_class": "gone"}
    spec = classes.with_class_choice(_product_sheet(), values, [BULKY]).field("shipping_class")
    assert spec.choices[-1] == "gone" and spec.word_for("gone") == "gone"


def test_no_classes_or_no_field_leaves_the_sheet_as_it_was() -> None:
    sheet = _product_sheet()
    assert classes.with_class_choice(sheet, {}, []) is sheet
    bare = SheetSpec("x", "X", (PageSpec("general", "General", (FieldSpec("sku", "SKU"),)),))
    assert classes.with_class_choice(bare, {}, [HEAVY]) is bare


# -- Generate Variations ------------------------------------------------------------------


def test_the_preview_counts_the_combinations_and_what_the_product_has() -> None:
    assert variations.variation_attributes(MUG) == [("Size", 2), ("Colour", 3)]
    lines = variations.preview_lines("Mug", SITE, MUG)
    assert lines[0] == (
        "Mug on Radio has 6 combinations of Size (2 values) and Colour (3 values), and "
        "2 variations now."
    )
    assert "Existing variations are not changed or removed." in lines[1]
    assert "Ctrl+Z deletes the ones made." in lines[2]


def test_a_product_that_is_not_variable_is_refused_with_the_reason() -> None:
    simple = {"id": 9, "type": "simple"}
    assert variations.refusal("Mug", SITE, simple) == (
        "Mug on Radio is a simple product, not a variable one, so it has no variations to "
        "make. Nothing was sent."
    )
    assert variations.refusal("Gift", SITE, {"type": "external"}).startswith(
        "Gift on Radio is an external product"
    )
    no_attributes = {**MUG, "attributes": [MUG["attributes"][2]]}
    assert "no attribute used for variations" in variations.refusal("Mug", SITE, no_attributes)
    assert variations.refusal("Mug", SITE, MUG) == ""


def test_generate_sends_no_delete_and_finds_the_new_variations() -> None:
    route = "wc/v3/products/9"
    api = Api({
        f"POST {route}/variations/generate": {"count": 4},
        route: {**MUG, "variations": [40, 41, 42, 43, 44, 45]},
    })
    count, made = variations.generate(api, 9, [40, 41])
    assert api.sent == [("POST", f"{route}/variations/generate", {})]
    assert (count, made) == (4, [42, 43, 44, 45])


def test_generate_reads_nothing_more_when_nothing_was_made() -> None:
    api = Api({"POST wc/v3/products/9/variations/generate": {"count": 0}})
    assert variations.generate(api, 9, [40]) == (0, [])


@pytest.mark.parametrize(
    ("count", "said"),
    [
        (0, "Made no variations of Mug on Radio: it already has every combination."),
        (1, "Made 1 variation of Mug on Radio."),
        (4, "Made 4 variations of Mug on Radio."),
        (
            50,
            "Made 50 variations of Mug on Radio, the most WooCommerce makes at once; Generate "
            "Variations again makes any still missing.",
        ),
    ],
)
def test_how_many_were_made_is_one_sentence_with_the_count(count: int, said: str) -> None:
    assert variations.made_sentence("Mug", SITE, count) == said
