"""Unit tests for ``quill.core.auth.provider``."""

from __future__ import annotations

import pytest

from quill.core.auth import (
    OAuthProvider,
    ProviderConfigError,
    ProviderRegistry,
    ProviderUnknownError,
)


def _provider(name: str = "bard") -> OAuthProvider:
    return OAuthProvider(
        name=name,
        authorize_url="https://example.test/authorize",
        token_url="https://example.test/token",
        client_id="quill-desktop",
        redirect_uri="http://127.0.0.1:0/callback",
        scopes=("search", "download"),
    )


def test_scope_str() -> None:
    assert _provider().scope_str == "search download"


def test_defaults() -> None:
    p = _provider()
    assert p.use_pkce is True
    assert p.broker_url is None
    assert p.device_code_url is None


@pytest.mark.parametrize("bad_name", ["", "Bard", "has space", "-lead", "a" * 64])
def test_invalid_name_rejected(bad_name: str) -> None:
    with pytest.raises(ProviderConfigError):
        _provider(bad_name)


def test_missing_urls_rejected() -> None:
    with pytest.raises(ProviderConfigError):
        OAuthProvider(
            name="bard",
            authorize_url="",
            token_url="https://example.test/token",
            client_id="x",
            redirect_uri="http://127.0.0.1:0/callback",
        )


def test_missing_client_id_rejected() -> None:
    with pytest.raises(ProviderConfigError):
        OAuthProvider(
            name="bard",
            authorize_url="https://example.test/authorize",
            token_url="https://example.test/token",
            client_id="",
            redirect_uri="http://127.0.0.1:0/callback",
        )


@pytest.mark.smoke
def test_registry_register_get_has_names() -> None:
    reg = ProviderRegistry()
    assert not reg.has("bard")
    reg.register(_provider("bard"))
    reg.register(_provider("radio"))
    assert reg.has("bard")
    assert reg.get("bard").client_id == "quill-desktop"
    assert reg.names() == ["bard", "radio"]


def test_registry_duplicate_rejected() -> None:
    reg = ProviderRegistry()
    reg.register(_provider("bard"))
    with pytest.raises(ProviderConfigError):
        reg.register(_provider("bard"))


def test_registry_unknown_raises() -> None:
    with pytest.raises(ProviderUnknownError):
        ProviderRegistry().get("nope")
