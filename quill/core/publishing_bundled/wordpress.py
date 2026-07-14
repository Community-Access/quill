"""Bundled-provider adapter for the in-tree WordPress implementation."""

from __future__ import annotations

from quill.core.publishing_adapters import BundledPublishingProviderAdapter
from quill.core.publishing_clients import publishing_provider_client
from quill.core.publishing_providers import (
    WORDPRESS_PROVIDER_ID,
    publishing_provider_definition,
)


def wordpress_bundled_provider_adapter() -> BundledPublishingProviderAdapter:
    """Return WordPress in the trusted bundled-provider package shape."""
    definition = publishing_provider_definition(WORDPRESS_PROVIDER_ID)
    client = publishing_provider_client(WORDPRESS_PROVIDER_ID)
    if definition is None or client is None:
        raise RuntimeError("The in-tree WordPress publishing provider is incomplete.")
    return BundledPublishingProviderAdapter(
        provider_id=WORDPRESS_PROVIDER_ID,
        definition=definition,
        client=client,
        network_capability_rationale=(
            "User-initiated WordPress REST API requests verify connections and browse, "
            "open, create, update, or publish content."
        ),
    )
