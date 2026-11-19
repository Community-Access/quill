"""WooCommerce's shipping classes in the Workbench, and choosing one by name (complete.md 2.3).

``wc/v3/products/shipping_classes``: each class has a name, a slug and a
description, and a product carries one by its slug in ``shipping_class``
(blank for none). A flat-rate method in a shipping zone can charge by class.

- **Shipping Classes**, under Shop: each class with its slug and how many
  products are in it. New, Change (name, slug, description) and Delete, each
  after a preview. Delete names the class and the site and is for good:
  WooCommerce keeps no Trash for a class, and its products are left with none.
- **Properties** on a product offers its shipping class as a choice by name
  (:func:`with_class_choice`), where the route's schema alone gives a slug to
  type.

Wx-free; the Workbench's commands are in :mod:`quill.ui.wordpress_workbench_shop_classes`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from quill.core.counted import plural
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import FieldKind, PageSpec, SheetSpec

__all__ = [
    "NONE_WORD",
    "ROUTE",
    "class_body",
    "class_preview",
    "class_row",
    "delete_lines",
    "load_classes",
    "with_class_choice",
]

ROUTE = f"{SHOP_NAMESPACE}/products/shipping_classes"
NONE_WORD = "No shipping class"
"""What a product with no shipping class shows on its Properties."""

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_KEYS = ("name", "slug", "description")


def _plain(value: Any) -> str:
    return " ".join(rendered(value).split())


def class_row(raw: Mapping[str, Any], site: str) -> WbRow:
    """One shipping class: its name, slug, how many products and its description."""
    name = _plain(raw.get("name")) or "Unnamed"
    slug = str(raw.get("slug", "") or "")
    description = _plain(raw.get("description"))
    count = int(raw.get("count", 0) or 0)
    return WbRow(
        kind="shop_shipping_class",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={"name": name, "slug": slug, "products": str(count)},
        detail=f"The shipping class {name} ({slug}), on {plural(count, 'product')}."
        + (f" {description}" if description else ""),
        subkind="woocommerce",
        raw={
            "name": name,
            "slug": slug,
            "description": description,
            "products": count,
            "_loaded": {"name": name, "slug": slug, "description": description},
        },
    )


def load_classes(api: Any, site: str) -> list[WbRow]:
    """Every shipping class, by name."""
    found = api.iter_collection(ROUTE, {}, per_page=100, max_pages=3)
    rows = [class_row(r, site) for r in found if isinstance(r, dict)]
    return sorted(rows, key=lambda r: r.title.casefold())


def class_body(old: Mapping[str, Any], answers: Mapping[str, str]) -> dict[str, Any]:
    """A class's changed fields (what was given, for a new one), checked.

    A blank slug on a new class lets WooCommerce make one from the name; on a
    class that has one, a blank slug keeps it.
    """
    name = " ".join(answers.get("name", "").split())
    slug = answers.get("slug", "").strip().lower()
    description = " ".join(answers.get("description", "").split())
    if not name:
        raise ShopValueError("A shipping class needs a name.")
    if slug and not _SLUG.match(slug):
        raise ShopValueError(
            f"{slug} is not a slug. A slug is lowercase letters and digits with a hyphen "
            "between words, such as heavy-items."
        )
    if not old:
        body: dict[str, Any] = {"name": name}
        if slug:
            body["slug"] = slug
        if description:
            body["description"] = description
        return body
    wanted = {"name": name, "slug": slug or str(old.get("slug", "")), "description": description}
    return {k: v for k, v in wanted.items() if str(old.get(k, "") or "") != v}


def class_preview(site: str, old: Mapping[str, Any], body: Mapping[str, Any]) -> list[str]:
    """What New or Change does, one line each, in words."""
    if not old:
        slug = f"slug {body['slug']}" if body.get("slug") else "a slug made from its name"
        lines = [f"A new shipping class on {site}: {body['name']}, with {slug}."]
        if body.get("description"):
            lines.append(f"Description: {body['description']}.")
        lines.append("A product is put in it from its Properties. Ctrl+Z deletes it again.")
        return lines
    lines = [f"The shipping class {old.get('name')} on {site}:"]
    for key in _KEYS:
        if key in body:
            was = str(old.get(key, "") or "") or "blank"
            lines.append(f"{key.capitalize()}: {was} becomes {body[key] or 'blank'}.")
    lines.append("Its products stay in it, and shipping zones' rates for it still apply.")
    return lines


def delete_lines(row: WbRow) -> list[str]:
    """The preview of Delete: what the class is, and what goes with it."""
    count = int(row.raw.get("products", 0) or 0)
    left = (
        f"Its {plural(count, 'product')} {'is' if count == 1 else 'are'} left with no shipping "
        "class, and"
        if count
        else "No product is in it, and"
    )
    return [
        row.detail,
        f"There is no Trash. {left} any rate a shipping zone sets for it stops applying.",
    ]


def with_class_choice(
    sheet: SheetSpec, values: dict[str, Any], classes: Sequence[Mapping[str, Any]]
) -> SheetSpec:
    """*sheet* with a product's shipping class chosen by name rather than typed as a slug.

    The choices are "No shipping class" and each class by name; a slug the
    shop no longer has stays offered as itself, so the sheet never changes
    a product just by opening. A sheet with no shipping class field, or a
    shop with no classes, is returned as it is.
    """
    pairs = [
        (str(c.get("slug", "") or ""), _plain(c.get("name")) or str(c.get("slug", "")))
        for c in classes
        if isinstance(c, Mapping) and c.get("slug")
    ]
    if not pairs or all(spec.key != "shipping_class" for spec in sheet.fields()):
        return sheet
    current = str(values.get("shipping_class") or "")
    pairs = [("", NONE_WORD), *sorted(pairs, key=lambda p: p[1].casefold())]
    if current and current not in {code for code, _word in pairs}:
        pairs.append((current, current))
    values["shipping_class"] = current
    pages: list[PageSpec] = []
    for page in sheet.pages:
        fields = tuple(
            replace(
                spec,
                kind=FieldKind.CHOICE,
                choices=tuple(code for code, _word in pairs),
                choice_words=tuple(word for _code, word in pairs),
                help="How this product is charged for shipping, by the shop's shipping "
                "classes. Shop > Shipping Classes makes and changes them.",
            )
            if spec.key == "shipping_class"
            else spec
            for spec in page.fields
        )
        pages.append(replace(page, fields=fields))
    return replace(sheet, pages=tuple(pages))
