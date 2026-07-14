from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import quill.core.publishing as publishing
import quill.core.publishing_clients as publishing_clients
import quill.core.publishing_validation as publishing_validation
from quill.core import paths
from quill.core.publishing import PublishingConnectionProfile
from quill.core.publishing_providers import (
    AUTH_METHOD_APP_PASSWORD,
    AUTH_METHOD_BROWSER_SESSION,
    AUTH_METHOD_EMAIL_LINK,
    AUTH_METHOD_PASSWORD,
    PUBLISHING_OPERATION_VERIFY,
    PublishingProviderDefinition,
    provider_auth_methods,
    provider_content_kind_label,
    provider_implemented_operations,
    provider_supported_auth_methods,
    provider_supported_operations,
    provider_supports_operation,
    publishing_auth_method_name,
    publishing_provider_help_text,
    register_publishing_provider,
    unregister_publishing_provider,
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
        publishing_clients,
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
    normalized = PublishingConnectionProfile.from_dict({
        "id": "pub-one",
        "label": "Site one",
        "provider_id": "wordpress",
        "site_url": "https://example.com",
        "auth_method": AUTH_METHOD_BROWSER_SESSION,
        "account_identifier": "writer",
    })
    assert normalized.auth_method == AUTH_METHOD_APP_PASSWORD


def test_verify_publishing_connection_reports_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Unauthorized(publishing_clients.HTTPError):
        def __init__(self) -> None:
            super().__init__(
                url="https://example.com/wp-json/wp/v2/users/me?context=edit",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=None,
            )

    monkeypatch.setattr(
        publishing_clients,
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


class _FakeSecondProviderClient:
    provider_id = "secondcms"

    def __init__(self) -> None:
        self.verified_profile: PublishingConnectionProfile | None = None
        self.verified_secret = ""

    def verify_connection(
        self,
        profile: object,
        secret: str,
        *,
        timeout_seconds: float,
    ) -> tuple[bool, str]:
        del timeout_seconds
        assert isinstance(profile, PublishingConnectionProfile)
        self.verified_profile = profile
        self.verified_secret = secret
        return True, f"Second CMS verified for {profile.account_identifier}."

    def browse_content(self, *_args, **_kwargs):
        return False, "not implemented", []

    def load_remote_item(self, *_args, **_kwargs):
        return False, "not implemented", None

    def update_remote_item(self, *_args, **_kwargs):
        return False, "not implemented", None

    def create_remote_item(self, *_args, **_kwargs):
        return False, "not implemented", None


def test_registered_second_provider_verification_uses_registered_client() -> None:
    client = _FakeSecondProviderClient()
    register_publishing_provider(
        PublishingProviderDefinition(
            id="secondcms",
            name="Second CMS",
            help_text="Second provider for framework-neutral publishing tests.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=(PUBLISHING_OPERATION_VERIFY,),
            implemented_operations=(PUBLISHING_OPERATION_VERIFY,),
            content_kind_labels={"article": "Article"},
            content_kind_plural_labels={"article": "Articles"},
        )
    )
    publishing_clients.register_publishing_provider_client(client)
    try:
        profile = PublishingConnectionProfile(
            id="pub-second",
            label="Second provider",
            provider_id="secondcms",
            site_url="https://second.example.com",
            auth_method=AUTH_METHOD_APP_PASSWORD,
            account_identifier="writer",
        )
        ok, message = publishing.verify_publishing_connection(profile, "second-secret")
    finally:
        publishing_clients.unregister_publishing_provider_client("secondcms")
        unregister_publishing_provider("secondcms")

    assert ok is True
    assert message == "Second CMS verified for writer."
    assert client.verified_profile is not None
    assert client.verified_profile.provider_id == "secondcms"
    assert client.verified_secret == "second-secret"


def test_second_provider_capabilities_gate_unimplemented_lifecycle_actions() -> None:
    client = _FakeSecondProviderClient()
    register_publishing_provider(
        PublishingProviderDefinition(
            id="secondcms",
            name="Second CMS",
            help_text="Second provider for framework-neutral publishing tests.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=(PUBLISHING_OPERATION_VERIFY,),
            implemented_operations=(PUBLISHING_OPERATION_VERIFY,),
            content_kind_labels={"article": "Article"},
            content_kind_plural_labels={"article": "Articles"},
        )
    )
    publishing_clients.register_publishing_provider_client(client)
    try:
        profile = PublishingConnectionProfile(
            id="pub-second",
            label="Second provider",
            provider_id="secondcms",
            site_url="https://second.example.com",
            auth_method=AUTH_METHOD_APP_PASSWORD,
            account_identifier="writer",
        )
        supported_operations = provider_supported_operations("secondcms")
        implemented_operations = provider_implemented_operations("secondcms")
        ok, message, items = publishing.browse_publishing_content(profile, "second-secret")
        publish_ok, publish_message, document = publishing.create_publishing_remote_item(
            profile,
            "second-secret",
            content_kind="article",
            title="Ready",
            document_text="Body",
            authoring_surface="markdown",
            status="publish",
        )
        schedule_ok, schedule_message, schedule_document = publishing.create_publishing_remote_item(
            profile,
            "second-secret",
            content_kind="article",
            title="Ready",
            document_text="Body",
            authoring_surface="markdown",
            scheduled_at=datetime(2099, 1, 1, tzinfo=UTC),
        )
    finally:
        publishing_clients.unregister_publishing_provider_client("secondcms")
        unregister_publishing_provider("secondcms")

    assert supported_operations == (PUBLISHING_OPERATION_VERIFY,)
    assert implemented_operations == (PUBLISHING_OPERATION_VERIFY,)
    assert ok is False
    assert message == "Second CMS browse is not implemented yet."
    assert items == []
    assert publish_ok is False
    assert publish_message == "Second CMS publish is not implemented yet."
    assert document is None
    assert schedule_ok is False
    assert schedule_message == "Second CMS schedule is not implemented yet."
    assert schedule_document is None


class _VerifyOnlyClient:
    provider_id = "verifyonly"

    def verify_connection(self, *_args, **_kwargs):
        return True, "Verified."


def _register_verify_only_provider(*, operation: str = PUBLISHING_OPERATION_VERIFY) -> None:
    register_publishing_provider(
        PublishingProviderDefinition(
            id="verifyonly",
            name="Verify Only",
            help_text="Provider/client validation fixture.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=(operation,),
            implemented_operations=(operation,),
            content_kind_labels={"article": "Article"},
            content_kind_plural_labels={"article": "Articles"},
        )
    )


def test_registered_provider_clients_validate_cleanly() -> None:
    assert publishing_validation.validate_registered_publishing_provider_clients() == ()


def test_provider_definition_metadata_validates_cleanly() -> None:
    assert publishing_validation.validate_publishing_provider_definition("wordpress") == ()


def test_provider_definition_validation_rejects_implemented_auth_not_supported() -> None:
    register_publishing_provider(
        PublishingProviderDefinition(
            id="verifyonly",
            name="Verify Only",
            help_text="Provider/client validation fixture.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=(PUBLISHING_OPERATION_VERIFY,),
            implemented_operations=(PUBLISHING_OPERATION_VERIFY,),
            content_kind_labels={"article": "Article"},
            content_kind_plural_labels={"article": "Articles"},
        )
    )
    try:
        issues = publishing_validation.validate_publishing_provider_definition("verifyonly")
    finally:
        unregister_publishing_provider("verifyonly")

    assert [issue.message for issue in issues] == [
        "Verify Only implements auth method 'password' but does not list it as supported."
    ]


def test_provider_definition_validation_rejects_unknown_auth_method() -> None:
    register_publishing_provider(
        PublishingProviderDefinition(
            id="verifyonly",
            name="Verify Only",
            help_text="Provider/client validation fixture.",
            default_content_format="html",
            supported_auth_methods=("token_magic",),
            implemented_auth_methods=("token_magic",),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=(PUBLISHING_OPERATION_VERIFY,),
            implemented_operations=(PUBLISHING_OPERATION_VERIFY,),
            content_kind_labels={"article": "Article"},
            content_kind_plural_labels={"article": "Articles"},
        )
    )
    try:
        issues = publishing_validation.validate_publishing_provider_definition("verifyonly")
    finally:
        unregister_publishing_provider("verifyonly")

    assert [issue.message for issue in issues] == [
        "Verify Only declares unknown publishing auth method 'token_magic'."
    ]


def test_provider_definition_validation_rejects_implemented_content_not_supported() -> None:
    register_publishing_provider(
        PublishingProviderDefinition(
            id="verifyonly",
            name="Verify Only",
            help_text="Provider/client validation fixture.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("note",),
            supported_operations=(PUBLISHING_OPERATION_VERIFY,),
            implemented_operations=(PUBLISHING_OPERATION_VERIFY,),
            content_kind_labels={"note": "Note"},
            content_kind_plural_labels={"note": "Notes"},
        )
    )
    try:
        issues = publishing_validation.validate_publishing_provider_definition("verifyonly")
    finally:
        unregister_publishing_provider("verifyonly")

    assert [issue.message for issue in issues] == [
        "Verify Only implements content kind 'note' but does not list it as supported."
    ]


def test_provider_definition_validation_requires_content_kind_labels() -> None:
    register_publishing_provider(
        PublishingProviderDefinition(
            id="verifyonly",
            name="Verify Only",
            help_text="Provider/client validation fixture.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=(PUBLISHING_OPERATION_VERIFY,),
            implemented_operations=(PUBLISHING_OPERATION_VERIFY,),
            content_kind_labels={},
            content_kind_plural_labels={},
        )
    )
    try:
        issues = publishing_validation.validate_publishing_provider_definition("verifyonly")
    finally:
        unregister_publishing_provider("verifyonly")

    assert [issue.message for issue in issues] == [
        "Verify Only implements content kind 'article' but has no singular label.",
        "Verify Only implements content kind 'article' but has no plural label.",
    ]


def test_provider_definition_validation_rejects_unknown_operation() -> None:
    register_publishing_provider(
        PublishingProviderDefinition(
            id="verifyonly",
            name="Verify Only",
            help_text="Provider/client validation fixture.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=("syndicate",),
            implemented_operations=("syndicate",),
            content_kind_labels={"article": "Article"},
            content_kind_plural_labels={"article": "Articles"},
        )
    )
    try:
        issues = publishing_validation.validate_publishing_provider_definition("verifyonly")
    finally:
        unregister_publishing_provider("verifyonly")

    assert [issue.message for issue in issues] == [
        "Verify Only declares unknown publishing operation 'syndicate'."
    ]


def test_provider_validation_reports_missing_client() -> None:
    _register_verify_only_provider()
    try:
        issues = publishing_validation.validate_registered_publishing_provider_clients()
    finally:
        unregister_publishing_provider("verifyonly")

    assert [issue.message for issue in issues] == [
        "Verify Only publishing provider has no registered client."
    ]


def test_provider_validation_reports_orphan_client() -> None:
    client = _VerifyOnlyClient()
    publishing_clients.register_publishing_provider_client(client)
    try:
        issues = publishing_validation.validate_registered_publishing_provider_clients()
    finally:
        publishing_clients.unregister_publishing_provider_client("verifyonly")

    assert [issue.message for issue in issues] == [
        "verifyonly publishing client has no registered provider definition."
    ]


def test_provider_validation_checks_declared_operation_methods() -> None:
    _register_verify_only_provider(operation="browse")
    publishing_clients.register_publishing_provider_client(_VerifyOnlyClient())
    try:
        issues = publishing_validation.validate_publishing_provider_client("verifyonly")
    finally:
        publishing_clients.unregister_publishing_provider_client("verifyonly")
        unregister_publishing_provider("verifyonly")

    assert provider_implemented_operations("verifyonly") == ()
    assert [issue.message for issue in issues] == [
        "Verify Only declares browse support but its client has no callable browse_content."
    ]


def test_unknown_provider_does_not_fall_back_to_wordpress() -> None:
    profile = PublishingConnectionProfile(
        id="pub-unknown",
        label="Mystery provider",
        provider_id="mystery",
        site_url="https://example.com",
        auth_method=AUTH_METHOD_APP_PASSWORD,
        account_identifier="writer",
    )

    ok, message = publishing.verify_publishing_connection(profile, "secret")

    assert ok is False
    assert message == "mystery publishing provider is not registered."
    assert provider_auth_methods("mystery") == ()
    assert provider_supported_auth_methods("mystery") == ()
    assert provider_content_kind_label("mystery", "entry") == "Entry"


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


def test_provider_metadata_supplies_operation_capabilities() -> None:
    assert "publish" in provider_implemented_operations("wordpress")
    assert "browse" in provider_supported_operations("wordpress")
    assert provider_supports_operation("wordpress", "publish") is True
    assert provider_supports_operation("mystery", "publish") is False
