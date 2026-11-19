"""Change Many Products... in the Workbench (complete.md 2.3, Shop: products/batch)."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress.workbench_shop_catalog import product_row  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import (  # noqa: E402
    SITE,
    _ref,
)
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import bench as _bench  # noqa: E402

bench = _bench

_MUG = product_row({"id": 9, "name": "Mug", "status": "publish", "regular_price": "20.00"}, SITE)
_CAP = product_row({"id": 10, "name": "Cap", "status": "publish", "regular_price": "10.00"}, SITE)


@pytest.fixture
def shop(bench, monkeypatch):
    answers: list[Any] = []

    def post(route: str, body: Any = None, **_p: Any) -> Any:
        bench.api.sent.append(("POST", route, body))
        return answers.pop(0) if answers else {"update": body.get("update", [])}

    monkeypatch.setattr(bench.api, "post", post)
    monkeypatch.setattr(bench.provider, "selected_rows", lambda: [_MUG, _CAP])
    bench.batch_answers = answers  # type: ignore[attr-defined]
    return bench


def test_a_sale_on_the_selection_previews_each_product_and_undoes(shop) -> None:
    a = shop.answers
    a.choices += [0]  # Put on sale
    a.texts += ["25"]
    shop.provider.do_bulk_edit_products(_ref("shop"), _MUG)
    preview = a.previews[-1]
    assert preview["summary"] == f"Change 2 products on {SITE}."
    assert preview["lines"] == ["Mug: 20.00, on sale at 15.00.", "Cap: 10.00, on sale at 7.50."]
    assert shop.api.sent[-1] == (
        "POST",
        "wc/v3/products/batch",
        {"update": [{"id": 9, "sale_price": "15.00"}, {"id": 10, "sale_price": "7.50"}]},
    )
    assert shop.said[-1] == f"Changed 2 of 2 products on {SITE}."
    assert (
        shop.provider.history.entries[-1].undo() == f"2 of 2 products on {SITE} are as they were."
    )
    assert shop.api.sent[-1][2] == {
        "update": [{"id": 9, "sale_price": ""}, {"id": 10, "sale_price": ""}]
    }


def test_a_refused_product_is_counted_and_reported(shop) -> None:
    shop.batch_answers.append({
        "update": [{"id": 9}, {"id": 10, "error": {"message": "Invalid price."}}]
    })
    shop.answers.choices += [4, 1]  # Set the status; draft
    shop.provider.do_bulk_edit_products(_ref("shop"), _MUG)
    assert shop.said[-1] == f"Changed 1 of 2 products on {SITE}. 1 was refused."
    assert shop.answers.reports[-1]["text"] == "Product 10: Invalid price."


def test_a_category_is_chosen_from_the_sites_own(shop, monkeypatch) -> None:
    plain = shop.api.get
    monkeypatch.setattr(
        shop.api,
        "get",
        lambda route, **p: (
            [{"id": 4, "name": "Mugs"}]
            if route == "wc/v3/products/categories"
            else plain(route, **p)
        ),
    )
    shop.answers.choices += [5, 0]  # Add a category; Mugs
    shop.provider.do_bulk_edit_products(_ref("shop"), _MUG)
    assert shop.answers.previews[-1]["lines"] == ["Mug: add Mugs.", "Cap: add Mugs."]
    assert shop.api.sent[-1][2]["update"][0] == {"id": 9, "categories": [{"id": 4}]}


def test_a_bad_percentage_changes_nothing(shop) -> None:
    shop.answers.choices += [0]
    shop.answers.texts += ["150"]
    shop.provider.do_bulk_edit_products(_ref("shop"), _MUG)
    assert shop.api.sent == [] and shop.said[-1].endswith("Nothing was changed.")
