"""GitHub Copilot device-flow config + token handoff (AI-19)."""

from __future__ import annotations

import pytest

from quill.core.ai import copilot_auth
from quill.core.ai.device_login import request_device_code, run_device_login


def test_unconfigured_without_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_GITHUB_CLIENT_ID", raising=False)
    assert copilot_auth.is_configured() is False
    with pytest.raises(ValueError):
        copilot_auth.github_device_flow_config()


def test_config_uses_github_endpoints_and_env_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_GITHUB_CLIENT_ID", "Iv1.deadbeef")
    assert copilot_auth.is_configured() is True
    config = copilot_auth.github_device_flow_config()
    assert config.client_id == "Iv1.deadbeef"
    assert config.device_authorization_url == copilot_auth.GITHUB_DEVICE_AUTH_URL
    assert config.token_url == copilot_auth.GITHUB_TOKEN_URL
    assert config.scope == copilot_auth.GITHUB_SCOPE


def test_apply_token_to_environment_bridges_to_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    copilot_auth.apply_token_to_environment("gho_session")
    import os

    assert os.environ["GITHUB_TOKEN"] == "gho_session"
    assert os.environ["GH_TOKEN"] == "gho_session"


def test_full_device_flow_with_real_poster_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    # End-to-end through the device_login engine using the poster contract:
    # request a code, then poll to an authorized token, all without a live server.
    monkeypatch.setenv("QUILL_GITHUB_CLIENT_ID", "Iv1.deadbeef")
    config = copilot_auth.github_device_flow_config()

    replies = iter([
        {
            "device_code": "dev",
            "user_code": "U-42",
            "verification_uri": "https://github.com/login/device",
            "interval": 1,
            "expires_in": 60,
        },
        {"error": "authorization_pending"},
        {"access_token": "gho_final", "token_type": "bearer"},
    ])

    def poster(url: str, fields: dict[str, str]) -> dict[str, object]:
        return next(replies)

    grant = request_device_code(config, poster=poster)
    assert grant.user_code == "U-42"
    result = run_device_login(
        config, grant, poster=poster, clock=lambda: 0.0, sleeper=lambda _s: None
    )
    assert result.status == "authorized"
    assert result.tokens["access_token"] == "gho_final"
