"""Tests for the shared radio HTTP identity (quill-radio #6)."""

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
    http_client._product_name = "Quill Radio"
    http_client._product_version = http_client.__version__
    yield
    http_client._product_name, http_client._product_version = saved


def test_user_agent_shape() -> None:
    ua = http_client.user_agent()
    assert ua.startswith("Quill Radio/")
    assert "github.com/Community-Access/quill" in ua
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
