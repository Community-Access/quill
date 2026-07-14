"""Trusted first-party publishing provider adapter contract.

Bundled adapters are imported explicitly by Quill. This module does not scan
packages, load third-party code, persist secrets, or perform network requests.
It only pairs reviewed provider metadata with its in-process client.

This module also defines the third-party publishing provider adapter shape
(``ThirdPartyPublishingProviderAdapter``) so the contract — id-conflict
checking, host-owned secrets, required worker execution — exists and is
tested ahead of time. Registering one always fails: live third-party
provider loading is not implemented. That is independent of this module —
third-party Quillin *code execution* in general remains locked off by the
``core.third_party_plugins`` feature flag (SEC-8, see
``quill/core/feature_catalog.py``) for QUILL 1.0, and the publishing-specific
contract here does not loosen, bypass, or duplicate that lock. Implementing
real loading is a separate, explicit product decision, not an engineering
detail to infer from this contract's shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.publishing_clients import PublishingProviderClient
    from quill.core.publishing_providers import PublishingProviderDefinition

HOST_OWNED_SECRET_ACCESS = "host_owned"
IN_PROCESS_EXECUTION = "in_process"
# Declared but not yet implemented: no untrusted publishing provider exists
# yet to validate a real subprocess/IPC worker boundary against (third-party
# provider loading remains locked off). Registration explicitly rejects this
# value below rather than silently accepting it, so the contract stays
# honest about what actually runs versus what is only planned.
WORKER_EXECUTION = "worker"


@dataclass(frozen=True, slots=True)
class BundledPublishingProviderAdapter:
    """A reviewed, package-facing contribution from a bundled provider."""

    provider_id: str
    definition: PublishingProviderDefinition
    client: PublishingProviderClient
    network_capability_rationale: str
    secret_access: str = HOST_OWNED_SECRET_ACCESS
    execution: str = IN_PROCESS_EXECUTION


_BUNDLED_PUBLISHING_PROVIDER_ADAPTERS: dict[str, BundledPublishingProviderAdapter] = {}


def register_bundled_publishing_provider(
    adapter: BundledPublishingProviderAdapter,
) -> None:
    """Register one trusted bundled adapter through the existing registries."""
    normalized = adapter.provider_id.strip().lower()
    definition_id = adapter.definition.id.strip().lower()
    client_id = adapter.client.provider_id.strip().lower()
    if not normalized:
        raise ValueError("Bundled publishing provider id is required.")
    if definition_id != normalized:
        raise ValueError("Bundled publishing provider definition id must match adapter id.")
    if client_id != normalized:
        raise ValueError("Bundled publishing provider client id must match adapter id.")
    if not adapter.network_capability_rationale.strip():
        raise ValueError("Bundled publishing provider network capability rationale is required.")
    if adapter.secret_access != HOST_OWNED_SECRET_ACCESS:
        raise ValueError("Bundled publishing provider secrets must remain host-owned.")
    if adapter.execution == WORKER_EXECUTION:
        raise ValueError("Worker-boundary bundled publishing providers are not implemented yet.")
    if adapter.execution != IN_PROCESS_EXECUTION:
        raise ValueError("Only trusted in-process bundled publishing providers are supported.")

    from quill.core.publishing_clients import register_publishing_provider_client
    from quill.core.publishing_providers import register_publishing_provider

    register_publishing_provider(adapter.definition)
    register_publishing_provider_client(adapter.client)
    _BUNDLED_PUBLISHING_PROVIDER_ADAPTERS[normalized] = adapter


def bundled_publishing_provider_adapters() -> tuple[BundledPublishingProviderAdapter, ...]:
    """Return explicitly registered first-party adapters in registration order."""
    return tuple(_BUNDLED_PUBLISHING_PROVIDER_ADAPTERS.values())


def bundled_publishing_provider_adapter(
    provider_id: str,
) -> BundledPublishingProviderAdapter | None:
    return _BUNDLED_PUBLISHING_PROVIDER_ADAPTERS.get(provider_id.strip().lower())


@dataclass(frozen=True, slots=True)
class ThirdPartyPublishingProviderAdapter:
    """A would-be contribution from a third-party publishing provider.

    Unlike :class:`BundledPublishingProviderAdapter`, ``secret_access`` and
    ``execution`` have no trusted defaults — a third-party adapter must state
    its policy explicitly rather than inherit one meant for reviewed code.
    """

    provider_id: str
    definition: PublishingProviderDefinition
    client: PublishingProviderClient
    network_capability_rationale: str
    secret_access: str
    execution: str


def register_third_party_publishing_provider(
    adapter: ThirdPartyPublishingProviderAdapter,
) -> None:
    """Validate a third-party adapter contract. Registration always fails.

    Every structural and security check below runs and is independently
    tested, so the contract is provably ready, but this function never adds
    anything to the live provider/client registries: live third-party
    publishing provider loading is not implemented yet.
    """
    normalized = adapter.provider_id.strip().lower()
    definition_id = adapter.definition.id.strip().lower()
    client_id = adapter.client.provider_id.strip().lower()
    if not normalized:
        raise ValueError("Third-party publishing provider id is required.")
    if definition_id != normalized:
        raise ValueError("Third-party publishing provider definition id must match adapter id.")
    if client_id != normalized:
        raise ValueError("Third-party publishing provider client id must match adapter id.")
    if not adapter.network_capability_rationale.strip():
        raise ValueError(
            "Third-party publishing provider network capability rationale is required."
        )
    if adapter.secret_access != HOST_OWNED_SECRET_ACCESS:
        raise ValueError("Third-party publishing provider secrets must remain host-owned.")
    if adapter.execution != WORKER_EXECUTION:
        raise ValueError(
            "Third-party publishing providers must declare worker execution; "
            "in-process execution is reserved for trusted bundled providers."
        )
    if bundled_publishing_provider_adapter(normalized) is not None:
        raise ValueError(
            f"Provider id '{normalized}' conflicts with an existing bundled publishing provider."
        )
    raise ValueError("Live third-party publishing provider loading is not implemented yet.")
