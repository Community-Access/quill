"""Coded errors for the QUILL Token Manager (``bard.md`` Part D.9).

Every failure carries a stable ``QUILL-AUTH-*`` code so a pasted message names
the exact branch. :class:`AuthError` is the coded base; the specific errors
inherit it (and so are not themselves direct ``CodedError`` subclasses, which is
why only the base is required to declare a code under GATE-EC -- but each sets
its own for runtime clarity).
"""

from __future__ import annotations

from quill.core.error_codes import CodedError


class AuthError(CodedError):
    """Base for all Token Manager failures."""

    code = "QUILL-AUTH-CORE-FAILED"


class ProviderUnknownError(AuthError):
    """No provider is registered under the requested name."""

    code = "QUILL-AUTH-PROVIDER-UNKNOWN"


class ProviderConfigError(AuthError):
    """A provider was registered with invalid or conflicting configuration."""

    code = "QUILL-AUTH-PROVIDER-CONFIG"


class FlowStateMismatchError(AuthError):
    """The ``state`` returned by the authorization server did not match (CSRF guard)."""

    code = "QUILL-AUTH-FLOW-STATE-MISMATCH"


class FlowTimeoutError(AuthError):
    """The interactive sign-in flow timed out or was cancelled."""

    code = "QUILL-AUTH-FLOW-TIMEOUT"


class RefreshInvalidGrantError(AuthError):
    """The refresh token was rejected (revoked or expired); a new sign-in is required."""

    code = "QUILL-AUTH-REFRESH-INVALID-GRANT"


class TokenUnavailableError(AuthError):
    """No valid access token is available and a refresh was not possible."""

    code = "QUILL-AUTH-TOKEN-UNAVAILABLE"


__all__ = [
    "AuthError",
    "FlowStateMismatchError",
    "FlowTimeoutError",
    "ProviderConfigError",
    "ProviderUnknownError",
    "RefreshInvalidGrantError",
    "TokenUnavailableError",
]
