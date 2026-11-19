"""Generate Variations: every missing combination of a variable product's attributes.

complete.md 2.3 (Shop), through ``wc/v3/products/{id}/variations/generate``.
WooCommerce makes a variation for each combination of the product's
attributes marked "Used for variations" that it does not have yet, and
answers with how many it made (``count``). Existing variations are never
changed: QUILL never sends ``delete``, which would remove the ones no
combination needs. WooCommerce makes at most :data:`MOST_AT_ONCE` in one
request, so a large product may need it again.

A product that is not variable, or has no attribute used for variations, is
refused here with the reason, and nothing is sent. The new variations' ids
are read from the product before and after, so Ctrl+Z deletes exactly those.

Wx-free; the Workbench's command is in :mod:`quill.ui.wordpress_workbench_shop_classes`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import prod
from typing import Any

from quill.core.counted import a_or_an, plural
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_shop_catalog import product_route

__all__ = [
    "MOST_AT_ONCE",
    "generate",
    "made_sentence",
    "preview_lines",
    "refusal",
    "variation_attributes",
    "variation_ids",
]

MOST_AT_ONCE = 50
"""WooCommerce's ``WC_MAX_LINKED_VARIATIONS``: the most one request makes."""


def variation_attributes(raw: Mapping[str, Any]) -> list[tuple[str, int]]:
    """Each attribute used for variations, with how many values it has."""
    found = []
    for attribute in raw.get("attributes") or []:
        if not isinstance(attribute, Mapping) or not attribute.get("variation"):
            continue
        options = [o for o in attribute.get("options") or [] if str(o).strip()]
        if options:
            found.append((rendered(attribute.get("name")) or "An attribute", len(options)))
    return found


def variation_ids(raw: Mapping[str, Any]) -> list[int]:
    """The ids of the variations a product has now, from its own ``variations`` list."""
    return [int(v) for v in raw.get("variations") or [] if str(v).isdigit()]


def refusal(name: str, site: str, raw: Mapping[str, Any]) -> str:
    """Why Generate Variations cannot run on this product, or "" when it can."""
    kind = str(raw.get("type", "") or "simple")
    if kind != "variable":
        return (
            f"{name} on {site} is {a_or_an(kind)} product, not a variable one, so it has no "
            "variations to make. Nothing was sent."
        )
    if not variation_attributes(raw):
        return (
            f"{name} on {site} has no attribute used for variations, so there is nothing to "
            "combine. Give it one in wp-admin under Product data, Attributes, with Used for "
            "variations ticked. Nothing was sent."
        )
    return ""


def preview_lines(name: str, site: str, raw: Mapping[str, Any]) -> list[str]:
    """What Generate Variations will do to *raw*, in words."""
    attributes = variation_attributes(raw)
    combos = prod(count for _name, count in attributes)
    have = len(variation_ids(raw))
    words = " and ".join(f"{a} ({plural(n, 'value')})" for a, n in attributes)
    return [
        f"{name} on {site} has {plural(combos, 'combination')} of {words}, and "
        f"{plural(have, 'variation')} now.",
        "WooCommerce makes a variation for each combination it does not have yet, at most "
        f"{MOST_AT_ONCE} at a time. Existing variations are not changed or removed.",
        "A new variation has no price, so shoppers cannot buy it until it has one (Edit a "
        "Variation). Ctrl+Z deletes the ones made.",
    ]


def made_sentence(name: str, site: str, count: int) -> str:
    """How many were made, in one sentence: always spoken, because it is a count."""
    if count <= 0:
        return f"Made no variations of {name} on {site}: it already has every combination."
    if count >= MOST_AT_ONCE:
        return (
            f"Made {plural(count, 'variation')} of {name} on {site}, the most WooCommerce makes "
            "at once; Generate Variations again makes any still missing."
        )
    return f"Made {plural(count, 'variation')} of {name} on {site}."


def generate(api: Any, product_id: int, before: Sequence[int]) -> tuple[int, list[int]]:
    """Ask WooCommerce for the missing combinations; how many it made, and their ids.

    *before* is the variation ids read for the preview. Off the UI thread.
    """
    route = product_route(product_id)
    answer = api.post(f"{route}/variations/generate", {})
    count = int(answer.get("count", 0) or 0) if isinstance(answer, Mapping) else 0
    if count <= 0:
        return 0, []
    after = api.get(route)
    known = set(before)
    made = [i for i in variation_ids(after if isinstance(after, Mapping) else {}) if i not in known]
    return count, made
