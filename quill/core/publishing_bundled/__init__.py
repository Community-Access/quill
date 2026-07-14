"""Explicit startup bootstrap for trusted bundled publishing providers."""

from __future__ import annotations

from quill.core.publishing_adapters import register_bundled_publishing_provider
from quill.core.publishing_bundled.wordpress import wordpress_bundled_provider_adapter


def bootstrap_bundled_publishing_providers() -> None:
    """Register reviewed first-party providers through their package adapters."""
    register_bundled_publishing_provider(wordpress_bundled_provider_adapter())
