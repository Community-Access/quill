"""PKCE (RFC 7636) helpers for public-client OAuth.

QUILL authenticates as a *public* OAuth client wherever the provider allows it
(``bard.md`` Part B.4): there is no client secret to embed, so nothing to
extract from the distributed app. PKCE binds an authorization request to the
client that made it via a high-entropy ``code_verifier`` and its S256
``code_challenge``.

Only the S256 method is implemented -- ``plain`` is deliberately unsupported.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass

# RFC 7636 section 4.1: the verifier is 43-128 chars from the unreserved set.
_UNRESERVED = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
_MIN_VERIFIER = 43
_MAX_VERIFIER = 128


@dataclass(frozen=True, slots=True)
class PkcePair:
    """A verifier and its derived challenge, with the method label ``S256``."""

    verifier: str
    challenge: str
    method: str = "S256"


def generate_code_verifier(length: int = 64) -> str:
    """Return a cryptographically random PKCE ``code_verifier``.

    ``length`` must be within RFC 7636's 43-128 bound. Characters are drawn
    uniformly from the unreserved set.
    """
    if not _MIN_VERIFIER <= length <= _MAX_VERIFIER:
        raise ValueError(
            f"code_verifier length must be {_MIN_VERIFIER}-{_MAX_VERIFIER}, got {length}"
        )
    return "".join(secrets.choice(_UNRESERVED) for _ in range(length))


def code_challenge_s256(verifier: str) -> str:
    """Return the base64url (unpadded) SHA-256 challenge for ``verifier`` (RFC 7636)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_pkce_pair(length: int = 64) -> PkcePair:
    """Generate a fresh verifier and its S256 challenge."""
    verifier = generate_code_verifier(length)
    return PkcePair(verifier=verifier, challenge=code_challenge_s256(verifier))


__all__ = [
    "PkcePair",
    "code_challenge_s256",
    "generate_code_verifier",
    "generate_pkce_pair",
]
