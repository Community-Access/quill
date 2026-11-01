"""GitHub Copilot device-flow config, per-app client ids and token store (AI-19)."""

from __future__ import annotations

import os

import pytest

import quill.core.github.token_store as token_store
from quill.core.ai import copilot_auth
from quill.core.ai.device_login import request_device_code, run_device_login
from quill.core.error_codes import CodedError
from quill.core.secrets import SecretsManager


class FakeBackend:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def load(self, cred_name: str) -> str:
        return self.store.get(cred_name, "")

    def save(self, cred_name: str, value: str) -> None:
        if value:
            self.store[cred_name] = value
        else:
            self.store.pop(cred_name, None)

    def delete(self, cred_name: str) -> bool:
        return self.store.pop(cred_name, None) is not None


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> FakeBackend:
    """One in-memory vault behind both the Copilot and the repository stores."""
    fake = FakeBackend()
    manager = SecretsManager(backend=fake)
    monkeypatch.setattr(copilot_auth, "default_secrets_manager", lambda: manager)
    monkeypatch.setattr(token_store, "default_secrets_manager", lambda: manager)
    return fake


# ---------------------------------------------------------------------------
# Client ids
# ---------------------------------------------------------------------------


def test_unconfigured_without_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.setitem(copilot_auth.CLIENT_IDS, "QUILL", "")
    assert copilot_auth.is_configured() is False
    with pytest.raises(ValueError):
        copilot_auth.github_device_flow_config()


def test_unavailable_error_is_coded_and_speakable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.setitem(copilot_auth.CLIENT_IDS, "QUILL Lite", "")
    with pytest.raises(copilot_auth.CopilotSignInUnavailable) as caught:
        copilot_auth.github_device_flow_config("QUILL Lite")
    assert isinstance(caught.value, CodedError)
    message = copilot_auth.sign_in_unavailable_message("QUILL Lite")
    assert message.startswith("Signing in to GitHub from inside QUILL Lite is not available yet.")
    assert "client id" not in message.lower()


def test_client_id_comes_from_the_table_per_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.setitem(copilot_auth.CLIENT_IDS, "QUILL", "Ov23liQUILL")
    monkeypatch.setitem(copilot_auth.CLIENT_IDS, "QUILL Lite", "Ov23liLITE")
    assert copilot_auth.client_id("QUILL") == "Ov23liQUILL"
    assert copilot_auth.client_id("QUILL Lite") == "Ov23liLITE"
    assert copilot_auth.client_id("Not An App") == ""
    assert copilot_auth.github_device_flow_config("QUILL Lite").client_id == "Ov23liLITE"


def test_table_names_quill_and_lite_and_ships_empty() -> None:
    # Jeff supplies the real ids; until then every value is an empty string.
    assert {"QUILL", "QUILL Lite"} <= set(copilot_auth.CLIENT_IDS)
    assert all(isinstance(value, str) for value in copilot_auth.CLIENT_IDS.values())


def test_env_override_wins_in_a_dev_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(copilot_auth.CLIENT_IDS, "QUILL", "Ov23liQUILL")
    monkeypatch.setenv("QUILL_GITHUB_CLIENT_ID", "Iv1.deadbeef")
    assert copilot_auth.is_configured() is True
    config = copilot_auth.github_device_flow_config()
    assert config.client_id == "Iv1.deadbeef"
    assert config.device_authorization_url == copilot_auth.GITHUB_DEVICE_AUTH_URL
    assert config.token_url == copilot_auth.GITHUB_TOKEN_URL
    assert config.scope == copilot_auth.GITHUB_SCOPE


def test_env_override_ignored_in_a_release_build(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import paths

    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    monkeypatch.setitem(copilot_auth.CLIENT_IDS, "QUILL", "")
    monkeypatch.setenv("QUILL_GITHUB_CLIENT_ID", "Iv1.deadbeef")
    assert copilot_auth.client_id() == ""


# ---------------------------------------------------------------------------
# Token store: per app, apart from the repository features
# ---------------------------------------------------------------------------


def test_each_app_has_its_own_entry(backend: FakeBackend) -> None:
    assert copilot_auth.token_ref("QUILL").cred_name == "quill-copilot-quill"
    assert copilot_auth.token_ref("QUILL Lite").cred_name == "quill-copilot-quill-lite"
    assert copilot_auth.persist_token("gho_quill", "QUILL") is True
    assert copilot_auth.persist_token("gho_lite", "QUILL Lite") is True
    assert copilot_auth.stored_token("QUILL") == "gho_quill"
    assert copilot_auth.stored_token("QUILL Lite") == "gho_lite"
    assert "quill-github-token" not in backend.store


def test_persist_never_touches_the_environment(backend: FakeBackend, absent_env) -> None:
    absent_env("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN")
    copilot_auth.persist_token("gho_secret", "QUILL")
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN"):
        assert name not in os.environ
    assert not hasattr(copilot_auth, "apply_token_to_environment")


def test_migration_leaves_shared_token_with_repository_features(backend: FakeBackend) -> None:
    # Before the split, Copilot's sign-in wrote into the repository entry.
    token_store.save_github_token("gho_shared")
    assert copilot_auth.stored_token("QUILL") is None
    assert copilot_auth.needs_own_sign_in("QUILL") is True
    assert token_store.load_github_token() == "gho_shared"

    copilot_auth.persist_token("gho_copilot", "QUILL")
    assert copilot_auth.needs_own_sign_in("QUILL") is False
    assert token_store.load_github_token() == "gho_shared"


def test_signing_out_of_copilot_keeps_the_repository_token(backend: FakeBackend) -> None:
    token_store.save_github_token("gho_repo")
    copilot_auth.persist_token("gho_copilot", "QUILL")
    copilot_auth.persist_token("gho_lite", "QUILL Lite")
    assert copilot_auth.forget_token("QUILL") is True
    assert copilot_auth.stored_token("QUILL") is None
    assert copilot_auth.stored_token("QUILL Lite") == "gho_lite"
    assert token_store.load_github_token() == "gho_repo"


def test_no_shared_token_means_no_migration_prompt(backend: FakeBackend) -> None:
    assert copilot_auth.needs_own_sign_in("QUILL") is False


# ---------------------------------------------------------------------------
# Device flow end to end
# ---------------------------------------------------------------------------


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
