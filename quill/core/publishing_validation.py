from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from quill.core.publishing_clients import publishing_provider_client
from quill.core.publishing_providers import (
    AUTH_METHOD_DEFINITIONS,
    PUBLISHING_OPERATION_BROWSE,
    PUBLISHING_OPERATION_CREATE,
    PUBLISHING_OPERATION_LOAD,
    PUBLISHING_OPERATION_PUBLISH,
    PUBLISHING_OPERATION_SCHEDULE,
    PUBLISHING_OPERATION_UPDATE,
    PUBLISHING_OPERATION_VERIFY,
    PUBLISHING_OPERATIONS,
    available_publishing_providers,
    provider_implemented_operations,
    publishing_provider_definition,
)

_OPERATION_METHODS = {
    PUBLISHING_OPERATION_VERIFY: "verify_connection",
    PUBLISHING_OPERATION_BROWSE: "browse_content",
    PUBLISHING_OPERATION_LOAD: "load_remote_item",
    PUBLISHING_OPERATION_UPDATE: "update_remote_item",
    PUBLISHING_OPERATION_CREATE: "create_remote_item",
    PUBLISHING_OPERATION_PUBLISH: "create_remote_item",
    PUBLISHING_OPERATION_SCHEDULE: "create_remote_item",
}


@dataclass(frozen=True, slots=True)
class PublishingProviderValidationIssue:
    provider_id: str
    message: str


def validate_publishing_provider_definition(
    provider_id: str,
) -> tuple[PublishingProviderValidationIssue, ...]:
    normalized = provider_id.strip().lower()
    definition = publishing_provider_definition(normalized)
    if definition is None:
        return (
            PublishingProviderValidationIssue(
                normalized,
                f"{normalized or 'Unknown provider'} publishing provider is not registered.",
            ),
        )

    issues: list[PublishingProviderValidationIssue] = []
    _extend_subset_issues(
        issues,
        normalized,
        definition.name,
        implemented=definition.implemented_auth_methods,
        supported=definition.supported_auth_methods,
        noun="auth method",
    )
    _extend_subset_issues(
        issues,
        normalized,
        definition.name,
        implemented=definition.implemented_content_kinds,
        supported=definition.supported_content_kinds,
        noun="content kind",
    )
    _extend_subset_issues(
        issues,
        normalized,
        definition.name,
        implemented=definition.implemented_operations,
        supported=definition.supported_operations,
        noun="operation",
    )
    _extend_unknown_issues(
        issues,
        normalized,
        definition.name,
        values=definition.supported_auth_methods + definition.implemented_auth_methods,
        known=AUTH_METHOD_DEFINITIONS,
        noun="auth method",
    )
    _extend_unknown_issues(
        issues,
        normalized,
        definition.name,
        values=definition.supported_operations + definition.implemented_operations,
        known=PUBLISHING_OPERATIONS,
        noun="operation",
    )
    for content_kind in definition.implemented_content_kinds:
        clean_kind = content_kind.strip().lower()
        if not clean_kind:
            issues.append(
                PublishingProviderValidationIssue(
                    normalized,
                    f"{definition.name} declares a blank implemented content kind.",
                )
            )
            continue
        if clean_kind not in definition.content_kind_labels:
            issues.append(
                PublishingProviderValidationIssue(
                    normalized,
                    (
                        f"{definition.name} implements content kind '{clean_kind}' but "
                        "has no singular label."
                    ),
                )
            )
        if clean_kind not in definition.content_kind_plural_labels:
            issues.append(
                PublishingProviderValidationIssue(
                    normalized,
                    (
                        f"{definition.name} implements content kind '{clean_kind}' but "
                        "has no plural label."
                    ),
                )
            )
    return tuple(issues)


def validate_publishing_provider_client(
    provider_id: str,
) -> tuple[PublishingProviderValidationIssue, ...]:
    normalized = provider_id.strip().lower()
    definition = publishing_provider_definition(normalized)
    if definition is None:
        return (
            PublishingProviderValidationIssue(
                normalized,
                f"{normalized or 'Unknown provider'} publishing provider is not registered.",
            ),
        )
    client = publishing_provider_client(normalized)
    if client is None:
        return (
            PublishingProviderValidationIssue(
                normalized,
                f"{definition.name} publishing provider has no registered client.",
            ),
        )
    issues: list[PublishingProviderValidationIssue] = []
    client_provider_id = str(getattr(client, "provider_id", "")).strip().lower()
    if client_provider_id != normalized:
        issues.append(
            PublishingProviderValidationIssue(
                normalized,
                (
                    f"{definition.name} publishing client id '{client_provider_id}' "
                    f"does not match provider id '{normalized}'."
                ),
            )
        )
    for operation in provider_implemented_operations(normalized):
        clean_operation = operation.strip().lower()
        method_name = _OPERATION_METHODS.get(clean_operation)
        if method_name is None:
            issues.append(
                PublishingProviderValidationIssue(
                    normalized,
                    f"{definition.name} declares unknown publishing operation '{operation}'.",
                )
            )
            continue
        method = getattr(client, method_name, None)
        if not callable(method):
            issues.append(
                PublishingProviderValidationIssue(
                    normalized,
                    (
                        f"{definition.name} declares {clean_operation} support but its "
                        f"client has no callable {method_name}."
                    ),
                )
            )
    return tuple(issues)


def validate_registered_publishing_provider_clients() -> tuple[
    PublishingProviderValidationIssue, ...
]:
    issues: list[PublishingProviderValidationIssue] = []
    definition_ids = {definition.id for definition in available_publishing_providers()}
    client_ids = set(_registered_provider_client_ids())
    for provider_id in sorted(definition_ids):
        issues.extend(validate_publishing_provider_definition(provider_id))
        issues.extend(validate_publishing_provider_client(provider_id))
    for provider_id in sorted(client_ids - definition_ids):
        issues.append(
            PublishingProviderValidationIssue(
                provider_id,
                f"{provider_id} publishing client has no registered provider definition.",
            )
        )
    return tuple(issues)


def _extend_subset_issues(
    issues: list[PublishingProviderValidationIssue],
    provider_id: str,
    provider_name: str,
    *,
    implemented: tuple[str, ...],
    supported: tuple[str, ...],
    noun: str,
) -> None:
    supported_set = {value.strip().lower() for value in supported if value.strip()}
    for value in implemented:
        clean_value = value.strip().lower()
        if not clean_value:
            issues.append(
                PublishingProviderValidationIssue(
                    provider_id,
                    f"{provider_name} declares a blank implemented {noun}.",
                )
            )
        elif clean_value not in supported_set:
            issues.append(
                PublishingProviderValidationIssue(
                    provider_id,
                    (
                        f"{provider_name} implements {noun} '{clean_value}' but does "
                        "not list it as supported."
                    ),
                )
            )


def _extend_unknown_issues(
    issues: list[PublishingProviderValidationIssue],
    provider_id: str,
    provider_name: str,
    *,
    values: tuple[str, ...],
    known: Iterable[object],
    noun: str,
) -> None:
    known_set = {str(value).strip().lower() for value in known}
    seen: set[str] = set()
    for value in values:
        clean_value = value.strip().lower()
        if not clean_value or clean_value in seen:
            continue
        seen.add(clean_value)
        if clean_value not in known_set:
            issues.append(
                PublishingProviderValidationIssue(
                    provider_id,
                    f"{provider_name} declares unknown publishing {noun} '{clean_value}'.",
                )
            )


def _registered_provider_client_ids() -> tuple[str, ...]:
    # Kept private so provider loading policy can change without exposing
    # the registry as mutable public API.
    import quill.core.publishing_clients as clients

    return tuple(clients._PUBLISHING_PROVIDER_CLIENTS)
