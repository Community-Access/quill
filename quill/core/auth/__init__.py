"""The QUILL Token Manager -- OAuth token lifecycle for every provider.

The package provides: the persisted
:class:`~quill.core.auth.token_bundle.TokenBundle`, PKCE helpers, the
:class:`~quill.core.auth.provider.OAuthProvider` config with its
:class:`~quill.core.auth.provider.ProviderRegistry`, the coded ``QUILL-AUTH-*``
error family, auth-state :mod:`~quill.core.auth.events`, the sign-in
:mod:`~quill.core.auth.flows` (Authorization Code + PKCE, device code), and the
refreshing :class:`~quill.core.auth.token_manager.TokenManager` (see
``bard.md`` Part D).

Everything here is wx-free, strict-typed, stores secrets only through
:mod:`quill.core.secrets` (never an OS vault directly), and performs the token
exchange through an injected poster (default: the reviewed, TLS-verified
:func:`quill.core.ai.oauth_poster.post_form`) so it adds no network egress site.
"""

from __future__ import annotations

from quill.core.auth.errors import (
    AuthError,
    FlowStateMismatchError,
    FlowTimeoutError,
    ProviderConfigError,
    ProviderUnknownError,
    RefreshInvalidGrantError,
    TokenUnavailableError,
)
from quill.core.auth.events import (
    REFRESH_FAILED,
    SIGNED_IN,
    SIGNED_OUT,
    AuthEvent,
    AuthListener,
)
from quill.core.auth.flows import (
    AuthRedirect,
    build_authorization_url,
    exchange_code,
    run_authorization_code_flow,
    run_device_code_flow,
)
from quill.core.auth.pkce import (
    PkcePair,
    code_challenge_s256,
    generate_code_verifier,
    generate_pkce_pair,
)
from quill.core.auth.provider import OAuthProvider, ProviderRegistry
from quill.core.auth.token_bundle import TokenBundle
from quill.core.auth.token_manager import Poster, TokenManager

__all__ = [
    "REFRESH_FAILED",
    "SIGNED_IN",
    "SIGNED_OUT",
    "AuthError",
    "AuthEvent",
    "AuthListener",
    "AuthRedirect",
    "FlowStateMismatchError",
    "FlowTimeoutError",
    "OAuthProvider",
    "PkcePair",
    "Poster",
    "ProviderConfigError",
    "ProviderRegistry",
    "ProviderUnknownError",
    "RefreshInvalidGrantError",
    "TokenBundle",
    "TokenManager",
    "TokenUnavailableError",
    "build_authorization_url",
    "code_challenge_s256",
    "exchange_code",
    "generate_code_verifier",
    "generate_pkce_pair",
    "run_authorization_code_flow",
    "run_device_code_flow",
]
