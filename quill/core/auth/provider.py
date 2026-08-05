"""OAuth provider configuration and the in-process provider registry.

An :class:`OAuthProvider` is a static description of one provider's endpoints
and client parameters. The :class:`ProviderRegistry` holds the set the app knows
about; new providers (BARD once its contract lands) register without any change
to the Token Manager itself.

A provider's ``name`` doubles as its Secrets Manager namespace, so it is
validated against the same short-segment pattern
(:data:`quill.core.secrets` uses ``quill-<namespace>-<name>``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.auth.errors import ProviderConfigError, ProviderUnknownError

# Matches the SecretRef namespace/name segment in quill.core.secrets so a
# provider name can be used directly as a secrets namespace.
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")


@dataclass(frozen=True, slots=True)
class OAuthProvider:
    """Static configuration for one OAuth provider."""

    name: str
    authorize_url: str
    token_url: str
    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...] = ()
    device_code_url: str | None = None
    revoke_url: str | None = None
    use_pkce: bool = True
    #: When set, the authorization-code exchange is routed through the QUILL
    #: broker (``bard.md`` Part E) which holds any confidential client secret;
    #: the desktop never possesses it.
    broker_url: str | None = None

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name):
            raise ProviderConfigError(
                f"provider name must match {_NAME_RE.pattern!r}; got {self.name!r}"
            )
        if not self.authorize_url or not self.token_url:
            raise ProviderConfigError(
                f"provider {self.name!r} requires authorize_url and token_url"
            )
        if not self.client_id:
            raise ProviderConfigError(f"provider {self.name!r} requires a client_id")

    @property
    def scope_str(self) -> str:
        """The space-delimited scope string for an authorization request."""
        return " ".join(self.scopes)


@dataclass(slots=True)
class ProviderRegistry:
    """A small, in-process registry of :class:`OAuthProvider` by name."""

    _providers: dict[str, OAuthProvider] = field(default_factory=dict)

    def register(self, provider: OAuthProvider) -> None:
        """Add ``provider``. Raises if a provider with the same name exists."""
        if provider.name in self._providers:
            raise ProviderConfigError(f"provider {provider.name!r} is already registered")
        self._providers[provider.name] = provider

    def get(self, name: str) -> OAuthProvider:
        """Return the provider, or raise :class:`ProviderUnknownError`."""
        try:
            return self._providers[name]
        except KeyError:
            raise ProviderUnknownError(f"no provider registered as {name!r}") from None

    def has(self, name: str) -> bool:
        return name in self._providers

    def names(self) -> list[str]:
        return sorted(self._providers)


__all__ = ["OAuthProvider", "ProviderRegistry"]
