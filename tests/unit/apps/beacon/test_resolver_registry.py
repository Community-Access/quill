"""Tests for the Quillin location-resolver registry and its use by uld.resolve."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from quill.apps.beacon import resolver_registry, uld


@pytest.fixture(autouse=True)
def _clear() -> Iterator[None]:
    resolver_registry.clear_resolvers()
    yield
    resolver_registry.clear_resolvers()


def _match(_loc: dict[str, Any], _content: str) -> dict[str, Any]:
    return {"matched": True, "confidence": 0.7, "position": {"offset": 3}, "message": "hit"}


def test_matching_resolver_returned() -> None:
    resolver_registry.register_resolver("ext.r", (), _match)
    result = resolver_registry.resolve_from_providers({}, "content")
    assert result is not None
    assert result["matched"] is True


def test_non_matched_resolution_ignored() -> None:
    resolver_registry.register_resolver("ext.r", (), lambda _l, _c: {"matched": False})
    assert resolver_registry.resolve_from_providers({}, "content") is None


def test_content_type_scoping() -> None:
    resolver_registry.register_resolver("ext.r", ("epub",), _match)
    assert resolver_registry.resolve_from_providers({}, "c", content_type="web") is None
    assert resolver_registry.resolve_from_providers({}, "c", content_type="epub") is not None


def test_faulty_resolver_skipped() -> None:
    def _boom(_l: dict[str, Any], _c: str) -> dict[str, Any] | None:
        raise RuntimeError("boom")

    resolver_registry.register_resolver("ext.bad", (), _boom)
    resolver_registry.register_resolver("ext.good", (), _match)
    assert resolver_registry.resolve_from_providers({}, "c") is not None


def test_register_replaces_by_id() -> None:
    resolver_registry.register_resolver("ext.r", (), _match)
    resolver_registry.register_resolver("ext.r", (), _match)
    assert resolver_registry.registered_resolver_ids() == ("ext.r",)


# -- consumption seam: uld.resolve falls through to a contributed resolver ----


def test_uld_resolve_uses_contributed_resolver_as_fallback() -> None:
    # An empty ULD: every built-in locator fails, so resolve reaches the Quillin
    # fallback layer, which places it.
    loc = uld.build_uld(resource_id="r1", location_type="web")
    resolver_registry.register_resolver(
        "ext.r",
        (),
        lambda _l, _c: {
            "matched": True,
            "confidence": 0.75,
            "position": {"offset": 10},
            "message": "matched by quillin",
        },
    )
    res = uld.resolve(loc, content="some page content")
    assert res.matched is True
    assert res.layer == "quillin"
    assert res.needs_review is True  # always below 0.9 (never a silent replace)
    assert res.position == {"offset": 10}


def test_uld_resolve_none_when_no_contributed_match() -> None:
    loc = uld.build_uld(resource_id="r1", location_type="web")
    res = uld.resolve(loc, content="some page content")
    assert res.matched is False
    assert res.layer == "none"


def test_uld_resolve_builtin_still_wins_over_quillin() -> None:
    # A native locator resolves before the Quillin layer is ever consulted.
    resolver_registry.register_resolver(
        "ext.r", (), lambda _l, _c: {"matched": True, "confidence": 0.8}
    )
    loc = uld.build_uld(resource_id="r1", native={"anchor": "top"})
    res = uld.resolve(loc, content="x")
    assert res.layer == "native"
