"""Auth-state events emitted by the Token Manager.

The manager emits these from core when a session is established, cleared, or its
refresh fails. The UI layer subscribes and marshals to the main thread with
``wx.CallAfter`` (that wiring lives in the UI, not here); core stays wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

#: A session was established (sign-in or first successful token store).
SIGNED_IN = "signed_in"
#: A session was cleared (sign-out / namespace wipe).
SIGNED_OUT = "signed_out"
#: A refresh failed because the refresh token was rejected; a new sign-in is needed.
REFRESH_FAILED = "refresh_failed"


@dataclass(frozen=True, slots=True)
class AuthEvent:
    """One auth-state change for a provider."""

    kind: str
    provider: str


AuthListener = Callable[[AuthEvent], None]

__all__ = ["REFRESH_FAILED", "SIGNED_IN", "SIGNED_OUT", "AuthEvent", "AuthListener"]
