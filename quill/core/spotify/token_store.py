"""Secure persistence for Spotify's OAuth tokens and the user's Client ID.

A thin wrapper over :mod:`quill.platform.windows.credential_store` (the same
unified env-var / portable-DPAPI / Credential-Manager store the AI keys use), in
the shape of :mod:`quill.core.github.token_store`. Nothing here is a secret in
source: the access/refresh tokens live only in the OS credential vault.

Two entries are kept:

* ``quill-spotify-tokens`` -- a JSON :class:`TokenBundle`
  (access_token, refresh_token, expires_at, scope).
* ``quill-spotify-client-id`` -- the user's own Spotify app Client ID (not a
  secret, but stored alongside the tokens so the whole connection lives in one
  place and clears together).

wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from quill.platform.windows.credential_store import delete_secret, load_secret, save_secret

_TOKENS_CRED = "quill-spotify-tokens"
_CLIENT_ID_CRED = "quill-spotify-client-id"


@dataclass(frozen=True, slots=True)
class TokenBundle:
    """The persisted Spotify session: tokens plus their absolute expiry."""

    access_token: str = ""
    refresh_token: str = ""
    #: Unix seconds after which ``access_token`` must be refreshed.
    expires_at: float = 0.0
    scope: str = ""

    @property
    def is_empty(self) -> bool:
        """True when no session is stored (nothing to refresh or use)."""
        return not self.access_token and not self.refresh_token

    @classmethod
    def from_token_response(cls, response: object, *, now: float) -> TokenBundle:
        """Build a bundle from a :class:`quill.core.spotify.auth.TokenResponse`.

        Takes ``response`` structurally (access_token / refresh_token /
        expires_in / scope attributes) to avoid a core import cycle, converting
        Spotify's relative ``expires_in`` to an absolute ``expires_at``.
        """
        return cls(
            access_token=str(getattr(response, "access_token", "")),
            refresh_token=str(getattr(response, "refresh_token", "")),
            expires_at=now + float(getattr(response, "expires_in", 0) or 0),
            scope=str(getattr(response, "scope", "")),
        )

    def to_json(self) -> str:
        return json.dumps({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scope": self.scope,
        })

    @classmethod
    def from_json(cls, raw: str) -> TokenBundle:
        """Parse a stored bundle; any malformed value yields an empty bundle."""
        if not raw:
            return cls()
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        expires_raw = data.get("expires_at", 0.0)
        try:
            expires_at = float(expires_raw)
        except (TypeError, ValueError):
            expires_at = 0.0
        return cls(
            access_token=str(data.get("access_token", "")),
            refresh_token=str(data.get("refresh_token", "")),
            expires_at=expires_at,
            scope=str(data.get("scope", "")),
        )


def load_tokens() -> TokenBundle:
    """Return the stored Spotify session, or an empty bundle when none is set."""
    return TokenBundle.from_json(load_secret(_TOKENS_CRED))


def save_tokens(bundle: TokenBundle) -> None:
    """Persist the Spotify session to the OS credential vault."""
    save_secret(_TOKENS_CRED, bundle.to_json())


def clear_tokens() -> bool:
    """Remove the stored session. Returns True when one existed."""
    return delete_secret(_TOKENS_CRED)


def load_client_id() -> str:
    """Return the stored Spotify app Client ID, or ``""`` when unset."""
    return load_secret(_CLIENT_ID_CRED)


def save_client_id(client_id: str) -> None:
    """Persist (or, when blank, clear) the Spotify app Client ID."""
    save_secret(_CLIENT_ID_CRED, client_id.strip())


def clear_client_id() -> bool:
    """Remove the stored Spotify app Client ID. Returns True when one existed."""
    return delete_secret(_CLIENT_ID_CRED)


__all__ = [
    "TokenBundle",
    "clear_client_id",
    "clear_tokens",
    "load_client_id",
    "load_tokens",
    "save_client_id",
    "save_tokens",
]
