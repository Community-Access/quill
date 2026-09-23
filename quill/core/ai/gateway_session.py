"""What this computer remembers about its hosted-AI account.

Two things, kept apart on purpose:

* **The token** is a secret and goes to the OS credential store -- Windows
  Credential Manager, or the DPAPI-encrypted portable file when QUILL is running
  from a folder. It is never written to the data directory, never logged, and
  never put in a settings file somebody might copy between machines along with
  their preferences.
* **Everything else** -- which account, where the service is, when this computer
  connected -- is ordinary state in ``<data>/ai/gateway.json``. None of it is
  sensitive, all of it is useful in a bug report, and keeping it out of the
  credential store means signing out is one delete rather than three.

The credential target is the same shape QUILL's own providers use
(``QUILL:assistant:<provider>:api-key``), so no new secure-storage code exists
anywhere -- just one new target string. That is deliberate: secure storage is
exactly the kind of code that should have one implementation and one set of
tests, not one per feature that needs a secret.

wx-free and strict-typed. The data directory is passed in rather than looked up,
so QuillLite and QUILL can each use their own without this module knowing which
one it is serving.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "CREDENTIAL_TARGET",
    "GatewaySession",
    "base_url",
    "clear_token",
    "load_session",
    "load_token",
    "save_session",
    "save_token",
    "support_id_for",
]

#: Where the device token lives. Same shape as every other provider credential
#: in QUILL, so the existing store handles it with no new code.
CREDENTIAL_TARGET = "QUILL:assistant:quill_gateway:api-key"

_STATE_FILE = "gateway.json"
_STATE_DIR = "ai"


def base_url() -> str:
    """Where the hosted service is, honouring an override.

    Overridable because the hostname is a deployment decision, not a product
    one: a fork, a staging box or somebody self-hosting the gateway needs a
    different value and should not need a different build to get it.
    """
    from quill.core.ai.gateway_client import DEFAULT_BASE_URL

    override = (os.environ.get("QUILL_AI_GATEWAY_URL") or "").strip()
    return (override or DEFAULT_BASE_URL).rstrip("/")


def support_id_for(user_or_device_id: str) -> str:
    """The short, speakable handle this account is known by in support.

    Accounts are pseudonymous UUIDs, which is the right privacy default and also
    means "somebody wrote in and I cannot find them" has no answer unless the
    person has something to quote. Eight characters, grouped, upper-case: short
    enough to read down a phone line, long enough that a prefix search lands on
    one account.

    Matches ``User.support_id`` on the server exactly. If one side ever changes
    how it groups them, support stops being able to match what it is told
    against what it can search.
    """
    flat = (user_or_device_id or "").replace("-", "").upper()
    if len(flat) < 8:
        return flat
    return f"{flat[:4]}-{flat[4:8]}"


@dataclass(frozen=True, slots=True)
class GatewaySession:
    """Everything non-secret this computer knows about its account."""

    device_id: str = ""
    base_url: str = ""
    connected_at: str = ""

    @property
    def signed_in(self) -> bool:
        return bool(self.device_id)

    @property
    def support_id(self) -> str:
        return support_id_for(self.device_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "base_url": self.base_url,
            "connected_at": self.connected_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> GatewaySession:
        if not isinstance(data, dict):
            return cls()
        return cls(
            device_id=str(data.get("device_id", "") or ""),
            base_url=str(data.get("base_url", "") or ""),
            connected_at=str(data.get("connected_at", "") or ""),
        )


def _state_path(data_dir: Path) -> Path:
    return data_dir / _STATE_DIR / _STATE_FILE


def load_session(data_dir: Path) -> GatewaySession:
    """What this computer remembers, or an empty session."""
    try:
        return GatewaySession.from_dict(read_json(_state_path(data_dir), default={}))
    except OSError:
        return GatewaySession()


def save_session(data_dir: Path, session: GatewaySession) -> None:
    """Remember this account. Atomic, like every other JSON write in QUILL."""
    path = _state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, session.to_dict())


# --------------------------------------------------------------------------- #
# The token
# --------------------------------------------------------------------------- #


def load_token() -> str:
    """This computer's device token, or "" when it has never signed in.

    Failure is silent and empty rather than raised: a credential store that
    cannot be read means "not signed in", which every caller already handles,
    and turning an unreadable keychain into an exception would take the whole
    editor down over a feature that is switched off by default.
    """
    try:
        from quill.platform.windows.credential_store import load_secret

        return (load_secret(CREDENTIAL_TARGET) or "").strip()
    except Exception:  # noqa: BLE001 - an unreachable store means "signed out"
        return ""


def save_token(token: str) -> bool:
    """Store the device token. ``False`` if the store refused it.

    A caller that gets ``False`` must say so rather than carrying on: a session
    that works until the app closes and then silently forgets is worse than one
    that never started, because the second is diagnosable.
    """
    try:
        from quill.platform.windows.credential_store import save_secret

        save_secret(CREDENTIAL_TARGET, token)
        return True
    except Exception:  # noqa: BLE001 - reported to the caller, never raised at a user
        return False


def clear_token() -> None:
    """Forget the device token. Never raises.

    Signing out must always succeed locally. Whether the server also revokes is
    a separate, best-effort question (``GatewayClient.revoke``) -- a user on a
    train with no signal who asks to sign out ends up signed out.
    """
    try:
        from quill.platform.windows.credential_store import delete_secret

        delete_secret(CREDENTIAL_TARGET)
    except Exception:  # noqa: BLE001 - already gone is the outcome we wanted
        pass


def sign_out(data_dir: Path) -> None:
    """Forget everything about this account, locally."""
    clear_token()
    save_session(data_dir, GatewaySession())
