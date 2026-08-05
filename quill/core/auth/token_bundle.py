"""The persisted OAuth session shape shared by every provider.

A :class:`TokenBundle` is what the Secrets Manager stores (via
``get_json`` / ``set_json``) and what the Token Manager reasons about when it
decides whether to refresh. Time is always passed in as ``now`` (absolute unix
seconds) so expiry logic is deterministic and unit-testable -- no wall-clock
call lives in here.

``expires_at`` is absolute unix seconds. A value of ``0`` means "expiry
unknown", which the expiry checks treat as already-expired so a bundle with an
unknown lifetime is refreshed rather than trusted indefinitely.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

_DEFAULT_SKEW_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class TokenBundle:
    """An OAuth session: tokens plus their absolute expiry."""

    access_token: str = ""
    refresh_token: str = ""
    #: Absolute unix seconds after which ``access_token`` must be refreshed;
    #: ``0`` means unknown (treated as expired).
    expires_at: float = 0.0
    scope: str = ""
    token_type: str = "Bearer"

    @property
    def is_empty(self) -> bool:
        """True when no session is stored (nothing to use or refresh)."""
        return not self.access_token and not self.refresh_token

    def is_expired(self, now: float, *, skew: float = _DEFAULT_SKEW_SECONDS) -> bool:
        """True when the access token is expired (or expires within ``skew`` seconds)."""
        return self.expires_at <= now + skew

    def needs_refresh(self, now: float, *, skew: float = _DEFAULT_SKEW_SECONDS) -> bool:
        """True when a refresh token exists and the access token is expired/expiring."""
        return bool(self.refresh_token) and self.is_expired(now, skew=skew)

    @classmethod
    def from_mapping(cls, data: dict[str, object], *, now: float) -> TokenBundle:
        """Build a bundle from a parsed token-endpoint JSON object.

        The safe counterpart to :meth:`from_token_response` for a plain ``dict``
        (what an HTTP poster returns): unknown keys are ignored and a missing or
        unparseable ``expires_in`` yields ``expires_at == 0`` (treated as expired).
        """
        expires_in = _coerce_float(data.get("expires_in", 0))
        expires_at = now + expires_in if expires_in > 0 else 0.0
        return cls(
            access_token=str(data.get("access_token", "") or ""),
            refresh_token=str(data.get("refresh_token", "") or ""),
            expires_at=expires_at,
            scope=str(data.get("scope", "") or ""),
            token_type=str(data.get("token_type", "") or "") or "Bearer",
        )

    @classmethod
    def from_token_response(cls, response: object, *, now: float) -> TokenBundle:
        """Build a bundle from a token-endpoint response object.

        Read structurally (``access_token`` / ``refresh_token`` / ``expires_in``
        / ``scope`` / ``token_type`` attributes) to avoid a hard import
        dependency, converting the relative ``expires_in`` to an absolute
        ``expires_at``. A missing or unparseable ``expires_in`` yields
        ``expires_at == 0`` (unknown -> treated as expired).
        """
        expires_in = _coerce_float(getattr(response, "expires_in", 0))
        expires_at = now + expires_in if expires_in > 0 else 0.0
        return cls(
            access_token=str(getattr(response, "access_token", "") or ""),
            refresh_token=str(getattr(response, "refresh_token", "") or ""),
            expires_at=expires_at,
            scope=str(getattr(response, "scope", "") or ""),
            token_type=str(getattr(response, "token_type", "") or "") or "Bearer",
        )

    def to_json(self) -> str:
        return json.dumps({
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scope": self.scope,
            "token_type": self.token_type,
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
        return cls(
            access_token=str(data.get("access_token", "") or ""),
            refresh_token=str(data.get("refresh_token", "") or ""),
            expires_at=_coerce_float(data.get("expires_at", 0.0)),
            scope=str(data.get("scope", "") or ""),
            token_type=str(data.get("token_type", "") or "") or "Bearer",
        )


def _coerce_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


__all__ = ["TokenBundle"]
