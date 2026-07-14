from __future__ import annotations

import pytest

from quill.core import publishing_clients, publishing_validation
from quill.core.publishing_adapters import (
    HOST_OWNED_SECRET_ACCESS,
    IN_PROCESS_EXECUTION,
    WORKER_EXECUTION,
    BundledPublishingProviderAdapter,
    ThirdPartyPublishingProviderAdapter,
    bundled_publishing_provider_adapter,
    register_bundled_publishing_provider,
    register_third_party_publishing_provider,
)
from quill.core.publishing_bundled import bootstrap_bundled_publishing_providers
from quill.core.publishing_bundled.wordpress import wordpress_bundled_provider_adapter
from quill.core.publishing_providers import (
    AUTH_METHOD_APP_PASSWORD,
    PUBLISHING_OPERATION_VERIFY,
    PublishingProviderDefinition,
    available_publishing_providers,
    publishing_provider_definition,
)


class _MismatchedClient:
    provider_id = "other"


def _definition(provider_id: str) -> PublishingProviderDefinition:
    return PublishingProviderDefinition(
        id=provider_id,
        name="Package CMS",
        help_text="Bundled adapter test provider.",
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


def test_wordpress_can_register_through_bundled_package_adapter() -> None:
    adapter = wordpress_bundled_provider_adapter()
    original_definition = publishing_provider_definition("wordpress")
    original_client = publishing_clients.publishing_provider_client("wordpress")

    register_bundled_publishing_provider(adapter)

    assert bundled_publishing_provider_adapter("wordpress") is adapter
    assert publishing_provider_definition("wordpress") is original_definition
    assert publishing_clients.publishing_provider_client("wordpress") is original_client
    assert adapter.secret_access == HOST_OWNED_SECRET_ACCESS
    assert adapter.execution == IN_PROCESS_EXECUTION
    assert adapter.network_capability_rationale
    assert publishing_validation.validate_registered_publishing_provider_clients() == ()


def test_normal_startup_bootstrap_preserves_wordpress_registry_identity() -> None:
    original_definition = publishing_provider_definition("wordpress")
    original_client = publishing_clients.publishing_provider_client("wordpress")

    bootstrap_bundled_publishing_providers()
    first_adapter = bundled_publishing_provider_adapter("wordpress")
    bootstrap_bundled_publishing_providers()
    second_adapter = bundled_publishing_provider_adapter("wordpress")

    assert first_adapter is not None
    assert second_adapter is not None
    assert second_adapter.definition is original_definition
    assert second_adapter.client is original_client
    assert publishing_provider_definition("wordpress") is original_definition
    assert publishing_clients.publishing_provider_client("wordpress") is original_client


def test_mismatched_adapter_is_rejected_before_registry_exposure() -> None:
    adapter = BundledPublishingProviderAdapter(
        provider_id="packagecms",
        definition=_definition("packagecms"),
        client=_MismatchedClient(),
        network_capability_rationale="User-initiated test requests.",
    )

    with pytest.raises(ValueError, match="client id must match"):
        register_bundled_publishing_provider(adapter)

    assert publishing_provider_definition("packagecms") is None
    assert publishing_clients.publishing_provider_client("packagecms") is None


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"network_capability_rationale": ""}, "rationale is required"),
        ({"secret_access": "provider_owned"}, "secrets must remain host-owned"),
        ({"execution": "cloud_function"}, "Only trusted in-process"),
        ({"execution": "worker"}, "Worker-boundary .* not implemented yet"),
    ],
)
def test_adapter_rejects_unsupported_security_or_runtime_shape(changes, message) -> None:
    values = {
        "provider_id": "packagecms",
        "definition": _definition("packagecms"),
        "client": type("PackageClient", (), {"provider_id": "packagecms"})(),
        "network_capability_rationale": "User-initiated test requests.",
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        register_bundled_publishing_provider(BundledPublishingProviderAdapter(**values))

    assert publishing_provider_definition("packagecms") is None
    assert publishing_clients.publishing_provider_client("packagecms") is None


def _third_party_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "provider_id": "thirdpartycms",
        "definition": _definition("thirdpartycms"),
        "client": type("ThirdPartyClient", (), {"provider_id": "thirdpartycms"})(),
        "network_capability_rationale": "User-initiated third-party requests.",
        "secret_access": HOST_OWNED_SECRET_ACCESS,
        "execution": WORKER_EXECUTION,
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"network_capability_rationale": ""}, "rationale is required"),
        ({"secret_access": "provider_owned"}, "secrets must remain host-owned"),
        ({"execution": IN_PROCESS_EXECUTION}, "must declare worker execution"),
        ({"execution": "cloud_function"}, "must declare worker execution"),
    ],
)
def test_third_party_adapter_rejects_malformed_shape_before_the_blanket_lock(
    overrides, message
) -> None:
    with pytest.raises(ValueError, match=message):
        register_third_party_publishing_provider(
            ThirdPartyPublishingProviderAdapter(**_third_party_values(**overrides))
        )

    assert publishing_provider_definition("thirdpartycms") is None
    assert publishing_clients.publishing_provider_client("thirdpartycms") is None


def test_third_party_adapter_rejects_id_mismatch() -> None:
    values = _third_party_values(client=type("ThirdPartyClient", (), {"provider_id": "other"})())

    with pytest.raises(ValueError, match="client id must match"):
        register_third_party_publishing_provider(ThirdPartyPublishingProviderAdapter(**values))


def test_third_party_adapter_rejects_id_conflicting_with_bundled_provider() -> None:
    values = _third_party_values(
        provider_id="wordpress",
        definition=_definition("wordpress"),
        client=type("ThirdPartyClient", (), {"provider_id": "wordpress"})(),
    )

    with pytest.raises(ValueError, match="conflicts with an existing bundled publishing provider"):
        register_third_party_publishing_provider(ThirdPartyPublishingProviderAdapter(**values))


def test_well_formed_third_party_adapter_is_still_rejected_and_never_exposed() -> None:
    """Proves the blanket lock: even a fully valid contract registers nothing."""
    adapter = ThirdPartyPublishingProviderAdapter(**_third_party_values())

    with pytest.raises(ValueError, match="not implemented yet"):
        register_third_party_publishing_provider(adapter)

    assert publishing_provider_definition("thirdpartycms") is None
    assert publishing_clients.publishing_provider_client("thirdpartycms") is None
    assert "thirdpartycms" not in {item.id for item in available_publishing_providers()}
