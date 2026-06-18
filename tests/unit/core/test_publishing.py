from __future__ import annotations

import json
from pathlib import Path

import pytest

import quill.core.publishing as publishing
from quill.core import paths
from quill.core.publishing import PublishingConnectionProfile
from quill.core.publishing_providers import (
    AUTH_METHOD_APP_PASSWORD,
    AUTH_METHOD_BROWSER_SESSION,
    AUTH_METHOD_EMAIL_LINK,
    provider_content_kind_label,
    provider_auth_methods,
    provider_supported_auth_methods,
    publishing_auth_method_name,
    publishing_provider_help_text,
)


@pytest.fixture
def publishing_data_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    data_dir = fake_home / "quill-data"
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    return data_dir


def test_publishing_connections_round_trip_multiple_profiles(
    publishing_data_env: Path,
) -> None:
    first = PublishingConnectionProfile(
        id="pub-one",
        label="Personal site",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    second = PublishingConnectionProfile(
        id="pub-two",
        label="Work blog",
        provider_id="wordpress",
        site_url="https://work.example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer@example.com",
    )
    store = publishing.PublishingConnectionStore(
        connections=[first, second],
        current_connection_id="pub-two",
    )
    publishing.save_publishing_connections(store)
    loaded = publishing.load_publishing_connections()
    assert len(loaded.connections) == 2
    assert loaded.current_connection_id == "pub-two"
    assert loaded.connections[0].label == "Personal site"
    assert loaded.connections[1].auth_method == AUTH_METHOD_APP_PASSWORD


def test_upsert_and_remove_publishing_connection(
    publishing_data_env: Path,
) -> None:
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    store = publishing.upsert_publishing_connection(profile)
    assert len(store.connections) == 1
    assert store.current_connection_id == "pub-one"

    updated = PublishingConnectionProfile(
        id="pub-one",
        label="Updated site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    store = publishing.upsert_publishing_connection(updated)
    assert len(store.connections) == 1
    assert store.connections[0].label == "Updated site one"

    store = publishing.remove_publishing_connection("pub-one")
    assert store.connections == []
    assert store.current_connection_id == ""


def test_publishing_secret_is_scoped_per_connection(
    monkeypatch: pytest.MonkeyPatch, publishing_data_env: Path
) -> None:
    saved: dict[str, str] = {}

    def _save(connection_id: str, secret: str) -> bool:
        saved[connection_id] = secret
        return True

    monkeypatch.setattr(publishing, "_save_secret_with_credential_manager", _save)
    monkeypatch.setattr(
        publishing,
        "_load_secret_from_credential_manager",
        lambda connection_id: saved.get(connection_id, ""),
    )
    publishing.save_publishing_secret("pub-one", "first-secret")
    publishing.save_publishing_secret("pub-two", "second-secret")
    assert publishing.load_publishing_secret("pub-one") == "first-secret"
    assert publishing.load_publishing_secret("pub-two") == "second-secret"


def test_publishing_secret_is_protected_on_disk(
    monkeypatch: pytest.MonkeyPatch, publishing_data_env: Path
) -> None:
    monkeypatch.setattr(publishing, "_save_secret_with_credential_manager", lambda *_a: False)
    monkeypatch.setattr(publishing, "_load_secret_from_credential_manager", lambda *_a: "")
    monkeypatch.setattr(publishing, "protect_secret", lambda secret: f"enc:{secret}")
    monkeypatch.setattr(publishing, "unprotect_secret", lambda secret: secret.removeprefix("enc:"))
    publishing.save_publishing_secret("pub-one", "app-secret")
    assert publishing.load_publishing_secret("pub-one") == "app-secret"


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_verify_publishing_connection_rejects_non_https_remote_endpoint() -> None:
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="http://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    ok, message = publishing.verify_publishing_connection(profile, "secret")
    assert ok is False
    assert "Only HTTPS endpoints are allowed" in message


def test_verify_publishing_connection_allows_local_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        publishing,
        "urlopen",
        lambda *_a, **_k: _FakeResponse({"id": 7, "name": "Writer"}),
    )
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Local site",
        provider_id="wordpress",
        site_url="http://localhost:8080",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    ok, message = publishing.verify_publishing_connection(profile, "secret")
    assert ok is True
    assert "Publishing connection verified for localhost:8080." == message


def test_unsupported_wordpress_auth_method_is_normalized_to_app_password() -> None:
    normalized = PublishingConnectionProfile.from_dict(
        {
            "id": "pub-one",
            "label": "Site one",
            "provider_id": "wordpress",
            "site_url": "https://example.com",
            "auth_method": AUTH_METHOD_BROWSER_SESSION,
            "account_identifier": "writer",
        }
    )
    assert normalized.auth_method == AUTH_METHOD_APP_PASSWORD


def test_verify_publishing_connection_reports_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Unauthorized(publishing.HTTPError):
        def __init__(self) -> None:
            super().__init__(
                url="https://example.com/wp-json/wp/v2/users/me?context=edit",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=None,
            )

    monkeypatch.setattr(
        publishing,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(_Unauthorized()),
    )
    profile = PublishingConnectionProfile(
        id="pub-one",
        label="Site one",
        provider_id="wordpress",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )
    ok, message = publishing.verify_publishing_connection(profile, "bad-secret")
    assert ok is False
    assert "Authentication failed" in message


def test_provider_metadata_keeps_ui_honest_about_implemented_auth_methods() -> None:
    methods = provider_auth_methods("wordpress")
    supported = provider_supported_auth_methods("wordpress")
    assert AUTH_METHOD_APP_PASSWORD in methods
    assert AUTH_METHOD_BROWSER_SESSION not in methods
    assert AUTH_METHOD_EMAIL_LINK not in methods
    assert AUTH_METHOD_BROWSER_SESSION not in supported
    assert AUTH_METHOD_EMAIL_LINK not in supported
    assert publishing_auth_method_name(AUTH_METHOD_EMAIL_LINK) == "Email sign-in link"
    assert "WordPress.com" in publishing_provider_help_text("wordpress")


def test_provider_metadata_supplies_content_kind_labels() -> None:
    assert provider_content_kind_label("wordpress", "post") == "Post"
    assert provider_content_kind_label("wordpress", "page") == "Page"
    assert provider_content_kind_label("wordpress", "post", plural=True) == "Posts"
    assert provider_content_kind_label("wordpress", "page", plural=True) == "Pages"
