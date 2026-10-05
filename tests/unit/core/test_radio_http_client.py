"""Tests for the family's one shared HTTP identity (quill-radio #6, check.md bug 1)."""

from __future__ import annotations

import pytest

from quill.core import http_client


@pytest.fixture(autouse=True)
def _restore_identity() -> object:
    # The identity is module-global; snapshot and restore so one test's
    # override never leaks into another. Also reset to the module default up
    # front: importing a standalone app (quill.apps.weather / quill.apps.radio
    # call set_product_identity at *import* time) otherwise leaves "Quill
    # Weather"/"Quill Radio" in the global, and under pytest-xdist that import
    # can land in this worker before test_user_agent_shape, failing it.
    saved = (http_client._product_name, http_client._product_version)
    http_client._product_name = http_client._DEFAULT_NAME
    http_client._product_version = http_client.__version__
    yield
    http_client._product_name, http_client._product_version = saved


def test_user_agent_shape() -> None:
    ua = http_client.user_agent()
    assert ua.startswith("QUILL/")
    assert "(+https://www.quillforall.org)" in ua
    # CBC stalls any User-Agent that mentions GitHub (check.md bug 1).
    assert "github" not in ua.lower()
    # A version follows the product name, and the project URL is parenthesized.
    assert "/" in ua
    assert ua.endswith(")")


def test_set_product_identity_overrides_name_and_version() -> None:
    http_client.set_product_identity("Quill Radio", "1.1.0")
    assert http_client.user_agent().startswith("Quill Radio/1.1.0 ")


def test_blank_overrides_are_ignored() -> None:
    before = http_client.user_agent()
    http_client.set_product_identity("", "")
    assert http_client.user_agent() == before


def test_cast_names_itself() -> None:
    http_client.set_product_identity("QUILL Cast", "2.0.0")
    assert http_client.user_agent() == "QUILL Cast/2.0.0 (+https://www.quillforall.org)"


def test_podcast_requests_say_they_come_from_a_podcast_app() -> None:
    # CBC answers this shape in half a second and stalls the bare one until
    # the timeout (probed against three CBC feeds, 2026-10-04).
    http_client.set_product_identity("QUILL Cast", "2.0.0")
    assert http_client.podcast_user_agent() == (
        "QUILL Cast/2.0.0 (podcast app; +https://www.quillforall.org)"
    )


def test_no_module_carries_its_own_github_user_agent() -> None:
    """One identity, read at request time. A module that grows its own copy is
    how the GitHub-bearing string survived in about forty places."""
    from pathlib import Path

    root = Path(http_client.__file__).resolve().parents[1]
    offenders = [
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if "github.com/Community-Access/quill)"
        in path.read_text(encoding="utf-8", errors="replace")
    ]
    assert offenders == []
