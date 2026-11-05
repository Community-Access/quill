"""Shared primitives for WordPress sign-in (wordpress.md 4.2, 4.3).

The error classes, the redacted :class:`Secret` and the loopback constants,
kept apart so :mod:`quill.core.wordpress.signin` and
:mod:`quill.core.wordpress.signin_loopback` can both use them without an
import cycle. Everything here is re-exported from ``signin``.
"""

from __future__ import annotations

import hmac
from typing import ClassVar
from urllib.parse import parse_qs, urlsplit

from quill.core.error_codes import CodedError

LOOPBACK_HOST = "127.0.0.1"
LOOPBACK_PATH = "/wordpress-done"


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class SignInError(CodedError):
    """Base for every sign-in failure. Messages never carry a secret."""

    code: ClassVar[str] = "QUILL-WORDPRESS-SIGNIN-FAILED"


class StateMismatchError(SignInError):
    """The ``state`` on the way back is missing or not the one we sent."""

    code: ClassVar[str] = "QUILL-WORDPRESS-SIGNIN-STATE-MISMATCH"


class MalformedRedirectError(SignInError):
    """The redirect lacks a field the flow needs."""

    code: ClassVar[str] = "QUILL-WORDPRESS-SIGNIN-MALFORMED-REDIRECT"


class AuthorizationDeniedError(SignInError):
    """The user (or the server) declined the WordPress.com authorization."""

    code: ClassVar[str] = "QUILL-WORDPRESS-SIGNIN-DENIED"


class TokenResponseError(SignInError):
    """The token endpoint answered with an error or an unusable body."""

    code: ClassVar[str] = "QUILL-WORDPRESS-SIGNIN-TOKEN-RESPONSE"


class ListenerError(SignInError):
    """The loopback listener could not start or was used out of order."""

    code: ClassVar[str] = "QUILL-WORDPRESS-SIGNIN-LISTENER"


# --------------------------------------------------------------------------
# Secrets
# --------------------------------------------------------------------------


class Secret:
    """A string that never shows itself in ``repr`` or ``str``.

    Call :meth:`reveal` at the one place the value is genuinely needed
    (Credential Manager, an ``Authorization`` header).
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret('***')"

    __str__ = __repr__

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Secret):
            return NotImplemented
        return hmac.compare_digest(self._value.encode(), other._value.encode())

    def __hash__(self) -> int:
        return hash(self._value)

    def __bool__(self) -> bool:
        return bool(self._value)


def query_params(url: str) -> dict[str, str]:
    """The query of ``url`` as single values (the first of any repeated key)."""
    return {
        key: values[0]
        for key, values in parse_qs(urlsplit(url).query, keep_blank_values=True).items()
    }
