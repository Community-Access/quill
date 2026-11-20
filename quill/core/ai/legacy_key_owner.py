"""Whose key the older, single-key store holds (2026-11 audit, gaps 8 and 13).

QUILL's first AI connection kept one key, for whichever provider was active
(``QUILL:assistant:api-key``). Per-provider keys came later, and the single
store stayed as a mirror of the active provider's key. Nothing recorded *which*
provider that mirror belonged to, so after the connection moved to another
company the old key could travel with it -- an OpenAI key sent to Anthropic --
and signing out of a provider left its mirror sending.

This module records the owner beside the key, in the same credential store,
and answers :func:`belongs_to` for every reader. A key goes only to the company
it belongs to. An install that saved its key before the owner was recorded is
judged from what it has: the key is the provider's own when it matches that
provider's saved key, never when it matches another's, and otherwise belongs
to the provider that was active when it was saved.

wx-free and strict-typed. It reaches back into ``assistant_ai`` for the store
primitives, as ``key_migration`` does, so tests that stand those in still apply.
"""

from __future__ import annotations

from quill.core import assistant_ai as _aai

__all__ = ["OWNER_TARGET", "belongs_to", "record_owner", "recorded_owner"]

#: The credential-store entry that names the owner of the single-key store.
OWNER_TARGET = "QUILL:assistant:api-key:owner"


def _normalized(provider: str) -> str:
    return (provider or "").strip().lower()


def record_owner(provider: str) -> None:
    """Remember *provider* as the owner of the single-key store ("" forgets it)."""
    owner = _normalized(provider)
    try:
        if owner:
            _aai._cs_save(OWNER_TARGET, owner)
        else:
            _aai._cs_delete(OWNER_TARGET)
    except Exception:  # noqa: BLE001 - no store: the older judgement applies
        pass


def recorded_owner() -> str:
    """The recorded owner, or "" when none was ever recorded."""
    try:
        return _normalized(_aai._cs_load(OWNER_TARGET) or "")
    except Exception:  # noqa: BLE001 - an unreadable store is "not recorded"
        return ""


def belongs_to(provider: str) -> bool:
    """Whether the key in the single-key store is *provider*'s to use."""
    target = _normalized(provider)
    if not target or target == "off":
        return False
    owner = recorded_owner()
    if owner:
        return owner == target
    legacy = (_aai.stored_assistant_api_key() or "").strip()
    if not legacy:
        return False
    own = (_aai.stored_provider_api_key(target) or "").strip()
    if own:
        return own == legacy
    for other in _aai._CLOUD_PROVIDERS:
        if other != target and (_aai.stored_provider_api_key(other) or "").strip() == legacy:
            return False
    try:
        active = _normalized(_aai.load_assistant_connection_settings().provider)
    except Exception:  # noqa: BLE001 - no readable connection: no owner to give it to
        return False
    return active == target
