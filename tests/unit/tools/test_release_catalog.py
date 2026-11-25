from __future__ import annotations

from quill.core.release_catalog import BY_KEY, PRODUCTS
from quill.tools.release_catalog_audit import problems


def test_release_catalog_agrees_with_every_release_consumer() -> None:
    assert problems() == []


def test_every_product_has_one_maintained_release_identity() -> None:
    assert len(PRODUCTS) == 12
    assert len(BY_KEY) == len(PRODUCTS)
    assert len({product.tag_prefix for product in PRODUCTS}) == len(PRODUCTS)
    assert len({product.asset_prefix.casefold() for product in PRODUCTS}) == len(PRODUCTS)


def test_preview_platform_wave_precedes_companions_social_and_beacon() -> None:
    first = {"quill", "quilllite", "radio", "cast", "transcribe", "converter"}
    companion = {"studio", "inkwell", "weather"}
    assert {key for key, product in BY_KEY.items() if product.wave == "platform"} == first
    assert {key for key, product in BY_KEY.items() if product.wave == "companion"} == companion
    assert BY_KEY["social"].wave == BY_KEY["beacon"].wave == "later"
    assert BY_KEY["player"].wave == "held"
