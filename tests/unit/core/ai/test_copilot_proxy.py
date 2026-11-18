from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.ai.copilot_proxy import resolve_system_proxy


@pytest.fixture
def proxy_config(monkeypatch: pytest.MonkeyPatch):
    proxies: dict[str, str] = {}
    bypass: list[str] = []
    monkeypatch.setattr("urllib.request.getproxies", lambda: proxies)
    monkeypatch.setattr("urllib.request.proxy_bypass", lambda host: host in bypass)
    return proxies, bypass


def test_https_request_uses_configured_system_proxy_without_forwarding_url(
    proxy_config,
) -> None:
    proxies, _bypass = proxy_config
    proxies["https"] = "http://proxy.example:8443"

    route = resolve_system_proxy(
        SimpleNamespace(url="https://copilot.example/chat?document=private")
    )

    assert route == "PROXY proxy.example:8443"
    assert "private" not in route


def test_proxy_bypass_is_explicitly_direct(proxy_config) -> None:
    _proxies, bypass = proxy_config
    bypass.append("localhost")

    assert resolve_system_proxy(SimpleNamespace(url="http://localhost:9000")) == "DIRECT"


def test_missing_or_credential_bearing_proxy_is_not_used(proxy_config) -> None:
    proxies, _bypass = proxy_config
    assert resolve_system_proxy(SimpleNamespace(url="https://api.example")) is None

    proxies["https"] = "http://user:secret@proxy.example:8080"
    assert resolve_system_proxy(SimpleNamespace(url="https://api.example")) is None


def test_invalid_proxy_port_falls_back_to_sdk_resolution(proxy_config) -> None:
    proxies, _bypass = proxy_config
    proxies["https"] = "http://proxy.example:99999"

    assert resolve_system_proxy(SimpleNamespace(url="https://api.example")) is None
